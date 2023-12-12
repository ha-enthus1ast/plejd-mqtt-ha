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
"""Healthcheck program used to check if plejd-mqtt is running."""

import argparse
import logging
import sys
import time

import yaml
from plejd_mqtt_ha.mdl.settings import PlejdSettings
from pydantic import ValidationError

STATUS_ERR = 1
STATUS_OK = 0


def is_program_running(plejd_settings: PlejdSettings) -> bool:
    """Check heartbeat and that program is running.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings to use for healthcheck

    Returns
    -------
    bool
        True if program is running, False otherwise
    """
    try:
        # Open the file
        heartbeat_file = plejd_settings.health_check_dir + plejd_settings.health_check_hearbeat_file
        with open(heartbeat_file, "r") as f:
            # Read the file
            contents = f.read()

        # Convert the contents to a float
        last_heartbeat = float(contents)

        # Get the current time
        current_time = time.time()

        # Check if the heartbeat is recent enough
        if current_time - last_heartbeat < plejd_settings.health_check_interval:
            return True
        else:
            return False
    except (FileNotFoundError, IOError, ValueError) as e:
        logging.error(f"Error during healthcheck: {e}")
        return False


def is_blueooth_connected(plejd_settings: PlejdSettings) -> bool:
    """Check if bluetooth is connected.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings to use for healthcheck

    Returns
    -------
    bool
        True if bluetooth is connected, False otherwise
    """
    try:
        # Open the file
        bt_status_file = plejd_settings.health_check_dir + plejd_settings.health_check_bt_file
        with open(bt_status_file, "r") as f:
            # Read the file
            contents = f.read()

        # Check if the first word is "connected"
        if contents.split()[0] == "connected":
            return True
        else:
            return False
    except (FileNotFoundError, IOError, ValueError) as e:
        logging.error(f"Error during healthcheck: {e}")
        return False


def is_mqtt_connected(plejd_settings: PlejdSettings) -> bool:
    """Check if MQTT is connected.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings to use for healthcheck

    Returns
    -------
    bool
        True if MQTT is connected, False otherwise
    """
    try:
        # Open the file
        mqtt_status_file = plejd_settings.health_check_dir + plejd_settings.health_check_bt_file
        with open(mqtt_status_file, "r") as f:
            # Read the file
            contents = f.read()

        # Check if the first word is "connected"
        if contents.split()[0] == "connected":
            return True
        else:
            return False
    except (FileNotFoundError, IOError, ValueError) as e:
        logging.error(f"Error during healthcheck: {e}")
        return False


def healthcheck(plejd_settings: PlejdSettings) -> int:
    """Perform healthcheck.

    Parameters
    ----------
    plejd_settings : PlejdSettings
        Settings to use for healthcheck

    Returns
    -------
    int
        STATUS_OK if healthcheck succeeds, STATUS_ERR if it fails
    """
    if not is_program_running(plejd_settings):
        logging.error("Plejd program is not running")
        return STATUS_ERR
    if not is_blueooth_connected(plejd_settings):
        logging.error("Bluetooth is not connected")
        return STATUS_ERR
    if not is_mqtt_connected(plejd_settings):
        logging.error("MQTT is not connected")
        return STATUS_ERR

    logging.info("All healthcheck passed")
    return STATUS_OK  # All checks passed, return OK


def main() -> int:
    """Entry point for the application script.

    Returns
    -------
    int
        Returns STATUS_OK if healthcheck succeeds, STATUS_ERR if it fails

    Raises
    ------
    ValueError
        If invalid log level is provided
    """
    parser = argparse.ArgumentParser(description="Healthcheck program")
    parser.add_argument("--loglevel", type=str, help="Set log level", default="ERROR")
    parser.add_argument(
        "-c", "--config", type=str, help="Path to the configuration file", default="/config"
    )
    args = parser.parse_args()

    numeric_level = getattr(logging, args.loglevel.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {args.loglevel}")

    logging.basicConfig(level=numeric_level, format="%(asctime)s %(levelname)s %(message)s")

    logging.info("Starting healthcheck")

    logging.info("Loading settings")

    try:
        with open(args.config, "r") as file:
            settings_yaml = yaml.safe_load(file)

        plejd_settings = PlejdSettings.parse_obj(settings_yaml)
    except FileNotFoundError:
        logging.critical("The settings.yaml file was not found.")
        return STATUS_ERR
    except yaml.YAMLError:
        logging.critical("There was an error parsing the settings.yaml file.")
        return STATUS_ERR
    except ValidationError as e:
        logging.critical(
            f"There was an error parsing the settings into a PlejdSettings object: {e}"
        )
        return STATUS_ERR

    return healthcheck(plejd_settings)


if __name__ == "__main__":
    sys.exit(main())
