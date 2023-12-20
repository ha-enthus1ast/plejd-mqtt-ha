# Copyright 2023 Viktor Karlquist <vkarlqui@gmail.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main plejd module.

Responsible for starting loading settings, performing health checks and creating devices.
"""

import asyncio
import datetime
import logging
import logging.handlers
import math
import os
import sys
import time

import ntplib
import pytz
import yaml
from plejd_mqtt_ha import constants
from plejd_mqtt_ha.bt_client import BTClient, PlejdBluetoothError
from plejd_mqtt_ha.mdl.combined_device import (
    BTDeviceError,
    CombinedDevice,
    CombinedDeviceTrigger,
    CombinedLight,
    CombinedSwitch,
    MQTTDeviceError,
)
from plejd_mqtt_ha.mdl.settings import PlejdSettings
from plejd_mqtt_ha.mdl.site import PlejdSite
from plejd_mqtt_ha.plejd_api import IncorrectCredentialsError, PlejdAPI, PlejdAPIError
from pydantic import ValidationError


def start(config: str, log_level: str, log_file: str, cache_file: str) -> None:
    """Start the Plejd service.

    This function will never return unless program exits, for whatever reason.

    Parameters
    ----------
    config : str
        Path to the config file
    log_level : str
        Log level to use
    log_file : str
        Path to the log file
    cache_file : str
        Path to the cache file
    """
    try:
        asyncio.run(_run(config, log_level, log_file, cache_file))
    except Exception as ex:
        logging.critical("Unhandled exception occured, exiting")
        logging.critical(ex)
        sys.exit()


async def _run(config: str, log_level: str, log_file: str, cache_file: str) -> None:
    """Entry point for starting and running the program.

    Parameters
    ----------
    config : str
        Path to the config file
    log_level : str
        Log level to use
    log_file : str
        Path to the log file
    cache_file : str
        Path to the cache file

    Raises
    ------
    ValueError
        If invalid log level is provided
    """
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    # Create dir for log file if it does not exist yet
    log_dir = os.path.dirname(log_file)
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    handler = logging.handlers.RotatingFileHandler(
        filename=log_file,
        maxBytes=constants.LOG_FILE_SIZE,  # 1 MB
        backupCount=constants.LOG_FILE_COUNT,  # 3 files
    )
    logging.basicConfig(
        level=numeric_level, format="%(asctime)s %(levelname)-8s %(message)s", handlers=[handler]
    )

    try:
        with open(config, "r") as file:
            settings_yaml = yaml.safe_load(file)

        plejd_settings = PlejdSettings.parse_obj(settings_yaml)
    except FileNotFoundError:
        logging.critical("The settings.yaml file was not found.")
        return
    except yaml.YAMLError:
        logging.critical("There was an error parsing the settings.yaml file.")
        return
    except ValidationError as e:
        logging.critical(
            f"There was an error parsing the settings into a PlejdSettings object: {e}"
        )
        return

    logging.info("Loaded Plejd settings..       [OK]")

    try:
        plejd_site = await _load_plejd_site(plejd_settings, cache_file)
    except IncorrectCredentialsError as err:
        logging.critical(str(err))
        return  # exit program if incorrect credentials

    logging.info("Plejd site loaded..           [OK]")

    plejd_bt_client = await _create_bt_client(plejd_site.crypto_key, plejd_settings)

    logging.info("Created Plejd BT client..     [OK]")
    discovered_devices = await _create_devices(plejd_settings, plejd_bt_client, plejd_site)
    if len(discovered_devices) <= 0:  # No devices created
        logging.critical("Failed to create Plejd devices, exiting")
        return
    logging.info(f"Created {len(discovered_devices)} Plejd devices.. [OK]")

    heartbeat_task = asyncio.create_task(write_health_data(plejd_settings, discovered_devices))
    update_time_task = asyncio.create_task(_update_plejd_time(plejd_settings, discovered_devices))

    await asyncio.gather(heartbeat_task, update_time_task)  # Wait indefinitely for the tasks


async def _update_plejd_time(
    plejd_settings: PlejdSettings, discovered_devices: list[CombinedDevice]
) -> None:
    """Update Plejd time continously.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings
    discovered_devices : list[CombinedDevice]
        List of discovered devices
    """
    bt_client = discovered_devices[0]._plejd_bt_client

    # Fetch timezone info
    if plejd_settings.timezone is not None:
        try:
            timezone = pytz.timezone(plejd_settings.timezone)
        except pytz.UnknownTimeZoneError:
            logging.warning("Unknown timezone, defaulting to local system timezone")
            timezone = None
    else:
        timezone = None

    while True:  # Run forever
        time_set = False

        # Get current time
        try:
            if plejd_settings.time_use_sys_time:
                current_sys_time = datetime.datetime.now(timezone)
            else:
                logging.info("Getting time from NTP server")
                ntp_client = ntplib.NTPClient()
                response = ntp_client.request("pool.ntp.org")
                current_sys_time = datetime.datetime.fromtimestamp(response.tx_time, timezone)
        except ntplib.NTPException:
            logging.warning("Failed to get time from NTP server, using system time instead")
            current_sys_time = datetime.datetime.now(timezone)

        # Update Plejd time
        for device in discovered_devices:
            try:
                ble_address = device._device_info.ble_address
                current_plejd_time = await bt_client.get_plejd_time(ble_address)

                current_plejd_time = current_plejd_time.replace(tzinfo=timezone)  # add timezone
                if abs(current_plejd_time - current_sys_time) > datetime.timedelta(
                    seconds=plejd_settings.time_update_interval
                ):
                    await bt_client.set_plejd_time(ble_address, current_sys_time)
                    logging.info(f"Updated Plejd time using device {device._device_info.name}")
                    time_set = True
                    break
                else:
                    logging.info(
                        f"Used device {device._device_info.name} to tell Plejd time is already up"
                        "to date"
                    )
                    time_set = True
                    break
            except PlejdBluetoothError:
                continue

        if not time_set:
            logging.warning("Failed to update Plejd time, no devices available")

        await asyncio.sleep(plejd_settings.time_update_interval)


async def write_health_data(
    plejd_settings: PlejdSettings, discovered_devices: list[CombinedDevice]
) -> None:
    """Write health data to files.

    Will continously write health data to files in the health_check_dir. This is used by the docker
    healthcheck script.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings
    discovered_devices : list[CombinedDevice]
        List of discovered devices
    """
    first_device = discovered_devices[0]  # Get first device
    bt_client = first_device._plejd_bt_client  # Get BT client
    mqtt_client = first_device._mqtt_entities[0].mqtt_client  # Get MQTT client

    # Write bluetooth health check file
    bt_health_check_file = plejd_settings.health_check_dir + plejd_settings.health_check_bt_file
    mqtt_health_check_file = plejd_settings.health_check_dir + plejd_settings.health_check_mqtt_file
    heartbeat_file = plejd_settings.health_check_dir + plejd_settings.health_check_hearbeat_file

    while True:  # Run forever
        # Retrieve status of BT and MQTT clients
        if bt_client.is_connected() and await bt_client.ping():
            bt_status = "connected"
        else:
            bt_status = "disconnected"
        if mqtt_client.is_connected():
            mqtt_status = "connected"
        else:
            mqtt_status = "disconnected"

        try:
            if plejd_settings.health_check:
                if not os.path.exists(plejd_settings.health_check_dir):
                    os.makedirs(plejd_settings.health_check_dir)
                # Indicate that the program is running
                with open(heartbeat_file, "w") as f:
                    f.write(str(time.time()))
                # Indicate that we are connected to Plejd bluetooth mesh
                with open(bt_health_check_file, "w") as f:
                    f.write(bt_status)
                # Indicate that we are connected to broker
                with open(mqtt_health_check_file, "w") as f:
                    f.write(mqtt_status)
            else:
                pass  # Do nothing if health check is disabled
        except (IOError, FileNotFoundError) as e:
            logging.error(f"Error writing to healthcheck file: {e}")
        finally:
            await asyncio.sleep(plejd_settings.health_check_interval)


async def _load_plejd_site(settings: PlejdSettings, cache_file: str) -> PlejdSite:
    # Load Plejd site from API, retry until success, or exit if credentials are incorrect
    api = PlejdAPI(settings)

    try:
        plejd_site = api.get_site(cache_file)
    except IncorrectCredentialsError:
        logging.critical("Failed to login to Plejd API, incorrect credentials in settings.json")
        raise
    except PlejdAPIError as err:  # Any other error, retry forever
        logging.error(f"Failed to retreive Plejd site: {str(err)})")

        async def _api_retry_loop() -> PlejdSite:
            logging.info("Entering Plejd API retry loop")
            retry_count = 0
            while True:
                try:
                    return api.get_site(cache_file)
                except PlejdAPIError as err:
                    logging.error(f"Failed to login to Plejd API: {str(err)})")
                    retry_count += 1
                    backoff_time = min(
                        constants.API_MAX_RETRY_TIME, math.pow(2, retry_count)
                    )  # Exponential backoff capped at API_MAX_RETRY_TIME
                    logging.error(f"Retrying in {backoff_time} seconds (retry {retry_count}")
                    await asyncio.sleep(backoff_time)

        plejd_site = await _api_retry_loop()  # retry until success

    logging.debug("Successfully logged in to Plejd API")

    return plejd_site


async def _create_bt_client(crypto_key: str, settings: PlejdSettings) -> BTClient:
    # Create Plejd BT client, retry until success

    bt_client = BTClient(crypto_key, settings)
    stay_connected = True

    if not await bt_client.connect(stay_connected):
        logging.error("Failed to connect to Plejd BT mesh")

        async def _bt_retry_loop() -> None:
            retry_count = 0
            while True:
                if await bt_client.connect(stay_connected):
                    return
                retry_count += 1
                backoff_time = min(
                    constants.BT_MAX_RETRY_TIME, math.pow(2, retry_count)
                )  # Exponential backoff capped at BT_MAX_RETRY_TIME
                logging.error(f"Retrying in {backoff_time} seconds (retry {retry_count}")
                await asyncio.sleep(backoff_time)

        await _bt_retry_loop()

    return bt_client


async def _create_devices(
    settings: PlejdSettings, bt_client: BTClient, plejd_site: PlejdSite
) -> list[CombinedDevice]:
    # Create every device connected to the Plejd Account

    combined_devices = []
    for device in plejd_site.devices:
        if device.category == constants.PlejdType.LIGHT.value:
            combined_device = CombinedLight(
                bt_client=bt_client, settings=settings, device_info=device
            )
        elif device.category == constants.PlejdType.DEVICE_TRIGGER.value:
            combined_device = CombinedDeviceTrigger(
                bt_client=bt_client, settings=settings, device_info=device
            )
        elif device.category == constants.PlejdType.SWITCH.value:
            combined_device = CombinedSwitch(
                bt_client=bt_client, settings=settings, device_info=device
            )
        else:
            logging.warning(f"{device.category} not supported")
            continue

        # Start device
        try:
            await combined_device.start()
            combined_devices.append(combined_device)
        except MQTTDeviceError as err:
            logging.warning(f"Skipping device {device.name}, cant create MQTT device: {str(err)}")
            continue
        except BTDeviceError as err:
            logging.warning(f"Skipping device {device.name}, cant create BT device: {str(err)}")
            continue
    return combined_devices
