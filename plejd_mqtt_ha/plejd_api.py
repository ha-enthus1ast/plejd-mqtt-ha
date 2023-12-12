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

"""Plejd API module.

Handles all communication with the Plejd cloud platform.
"""

import json
import logging
from typing import Optional

import plejd_mqtt_ha.constants
import requests
from plejd_mqtt_ha.mdl.bt_device_info import BTDeviceInfo, BTLightInfo
from plejd_mqtt_ha.mdl.settings import PlejdSettings
from plejd_mqtt_ha.mdl.site import PlejdSite
from pydantic import BaseModel


class PlejdAPIError(Exception):
    """Exception raised for errors in the Plejd Bluetooth connection."""

    def __init__(self, message: str):
        """Initialize PlejdAPIError class.

        Parameters
        ----------
        message : str
            Error message
        """
        self.message = message
        super().__init__(self.message)


class UnknownResponseError(PlejdAPIError):
    """Exception raised when the Plejd API returns an unknown response."""

    pass


class UnsupportedDeviceTypeError(PlejdAPIError):
    """Exception raised when the Plejd API returns an unsupported device type."""

    pass


class IncorrectCredentialsError(PlejdAPIError):
    """Exception raised when the supplied credentials are incorrect."""

    pass


class CacheFileError(PlejdAPIError):
    """Exception raised when cache file cannot be loaded or stored."""

    pass


class PlejdAPI:
    """PlejdAPI class that handles all communication with the Plejd cloud platform.

    Data does not need to be fetched unless devices has been added and/or modified, ie data can be
    cached locally.
    """

    class PlejdDeviceType(BaseModel):
        """Types of devices from Plejd API."""

        name: str
        """Name of the specific type
        """
        device_category: str
        """Which type of device category does it belong to
        """
        dimmable: bool = False
        """Whether or not the device can be dimmed
        """
        broadcast_clicks: bool = False
        """Whether or not it can broadcast clicks, ie a button etc
        """

    def __init__(self, settings: PlejdSettings) -> None:
        """Initialize PlejdAPI class.

        Parameters
        ----------
        settings : PlejdSettings
            Settings for the Plejd API
        """
        self._settings = settings.api
        self._session_token = None

    def login(self) -> None:
        """Login to plejd API. This is required to get the site information."""
        headers = {
            "X-Parse-Application-Id": plejd_mqtt_ha.constants.API_APP_ID,
            "Content-Type": "application/json",
        }

        data = {"username": self._settings.user, "password": self._settings.password}

        try:
            response = requests.post(
                plejd_mqtt_ha.constants.API_BASE_URL + plejd_mqtt_ha.constants.API_LOGIN_URL,
                json=data,
                headers=headers,
                timeout=self._settings.timeout,
            )
            response.raise_for_status()
            response_json = response.json()
            if "sessionToken" not in response_json:
                raise ValueError("Failed to parse response as JSON")
        except requests.HTTPError as err:
            if response.status_code == 401:
                logging.error("Login failed due to incorrect credentials")
                raise IncorrectCredentialsError(
                    "Login failed due to incorrect credentials"
                ) from err
            else:
                logging.error(f"HTTP error occurred: {str(err)}")
                raise PlejdAPIError(f"HTTP error occurred: {str(err)}") from err
        except requests.RequestException as err:
            logging.error(f"Login request failed: {str(err)}")
            raise PlejdAPIError(f"Login request failed: {str(err)}") from err
        except ValueError as err:
            logging.error(f"Login parse failed:  {str(err)}")
            raise UnknownResponseError(f"Login parse failed:  {str(err)}") from err

        self._session_token = response_json["sessionToken"]

    def get_site(self) -> PlejdSite:
        """Get plejd site.

        If no site name in settings, it will take the first site in the list. Also responsible for
        logging in to the API if not already logged in.

        Returns
        -------
        PlejdSite
            Plejd site with site_name or first plejd site in list

        Raises
        ------
        PlejdAPIError
            If the request fails
        UnknownResponseError
            If the response is not as expected
        CacheFileError
            If the cache file is not found
        IncorrectCredentialsError
            If the credentials are incorrect to login to the Plejd API
        """
        # Check cache policy
        if self._settings.cache_policy == "FIRST_CACHE":
            # Fetch from cache if exists, otherwise use cache
            logging.info("Fetching site from cache if possible, otherwise using API")
            try:
                plejd_site = self._get_site_from_cache()
            except CacheFileError as err:
                logging.warning(f"Failed to get site from cache: {str(err)}")
                logging.info("Fetching site from Plejd API")
                try:
                    plejd_site = self._get_site_from_api()
                except (IncorrectCredentialsError, PlejdAPIError, UnknownResponseError) as err:
                    logging.error(f"Failed to get site from Plejd API: {str(err)}")
                    raise
        elif self._settings.cache_policy == "NO_CACHE":
            # Fetch from API, otherwise raise error
            logging.info("Fetching site from Plejd API")
            try:
                # Attempt to fetch from API, do not store site afterwards
                plejd_site = self._get_site_from_api()
            except (IncorrectCredentialsError, PlejdAPIError, UnknownResponseError) as err:
                logging.warning(f"Failed to get site from API: {str(err)}")
                raise
        elif self._settings.cache_policy == "NEEDED_CACHE":
            # Fetch from API, otherwise use cache
            logging.info("Fetching site from API if possible, otherwise using cache")
            try:
                plejd_site = self._get_site_from_api()
            except (IncorrectCredentialsError, PlejdAPIError, UnknownResponseError) as err:
                logging.warning(f"Failed to get site from API: {str(err)}")
                logging.info("Fetching site from cache")
                try:
                    plejd_site = self._get_site_from_cache()
                except CacheFileError as err:
                    logging.error(f"Failed to get site from cache: {str(err)}")
                    raise

        return plejd_site

    def _get_site_from_cache(self) -> PlejdSite:
        """Get site from cache.

        Returns
        -------
        PlejdSite
            Plejd site
        """
        json_site = self._get_json_site_from_cache()

        plejd_site = PlejdSite(
            name=json_site["site"]["title"],
            site_id=json_site["site"]["siteId"],
            crypto_key=json_site["plejdMesh"]["cryptoKey"],
            devices=self._get_devices(json_site),
        )

        return plejd_site

    def _get_site_from_api(self) -> PlejdSite:
        """Get site from Plejd API.

        Returns
        -------
        PlejdSite
            Plejd site
        """
        self.login()
        site_data = self._get_site_data()
        site_id = self._get_site_id(site_data, self._settings.site)
        json_site = self._get_json_site_from_api(site_id)

        try:
            self.store_json_site_to_cache(json_site)
        except CacheFileError as err:
            # Only log error if not able to store site to cache, ok to continue
            logging.warning(f"Failed to store site to cache: {str(err)}")

        plejd_site = PlejdSite(
            name=json_site["site"]["title"],
            site_id=site_id,
            crypto_key=json_site["plejdMesh"]["cryptoKey"],
            devices=self._get_devices(json_site),
        )

        return plejd_site

    def _get_json_site_from_api(self, site_id: str) -> dict:
        """Get json site data from Plejd API.

        Parameters
        ----------
        site_id : str
            Id of the site to fetch JSON content from

        Returns
        -------
        str:
            JSON content of the site
        """
        headers = {
            "X-Parse-Application-Id": plejd_mqtt_ha.constants.API_APP_ID,
            "X-Parse-Session-Token": self._session_token,
            "Content-Type": "application/json",
        }

        data = {
            "siteId": site_id,
        }

        response = requests.post(
            plejd_mqtt_ha.constants.API_BASE_URL + plejd_mqtt_ha.constants.API_SITE_DETAILS_URL,
            json=data,
            headers=headers,
            timeout=10,
        )
        try:
            response_json = response.json()
            if "result" not in response_json:
                raise UnknownResponseError(f"Failed to get site: {response_json}")
            logging.info("Got site from Plejd API")
        except (ValueError, UnknownResponseError) as err:
            logging.error(f"Failed to parse response as JSON: {str(err)}")
            raise UnknownResponseError(f"Failed to parse response as JSON: {str(err)}") from err

        return response_json["result"][0]

    def _get_site_id(self, site_data: dict, site_name: Optional[str]) -> str:
        """Get site id from site data.

        Will return the first site if no site name is specified in settings.

        Parameters
        ----------
        site_data : dict
            JSON content of the site
        site_name : Optional[str]
            Name of the site to fetch, by default None

        Returns
        -------
        str
            site id
        """
        # Fetch site ID and name
        site_id = ""
        if site_name is not None:
            for site in site_data:
                if site["site"]["title"] == site_name:
                    site_id = site["site"]["siteId"]
                    break
            if not site_id:
                old_site_name = site_name  # Store for warning message
                site_name = site_data["result"][0]["site"]["title"]
                site_id = site_data["result"][0]["site"]["site"]["siteId"]
                logging.warning(
                    f"Site {old_site_name} not found in available sites, using {site_name}"
                )
        else:
            site_id = site_data[0]["site"]["siteId"]
        return site_id

    def _get_site_data(self) -> dict:
        """Get site data from Plejd API.

        Site data contains information about all available sites.

        Returns
        -------
        dict
            JSON content of the site

        Raises
        ------
        PlejdAPIError
            If the request fails
        UnknownResponseError
            If the response is not as expected
        """
        # Fetch site information from Plejd API
        headers = {
            "X-Parse-Application-Id": plejd_mqtt_ha.constants.API_APP_ID,
            "X-Parse-Session-Token": self._session_token,
            "Content-Type": "application/json",
        }
        try:
            response = requests.post(
                plejd_mqtt_ha.constants.API_BASE_URL + plejd_mqtt_ha.constants.API_SITE_LIST_URL,
                headers=headers,
                timeout=10,
            )
            response.raise_for_status()
            response_json = response.json()
            if "result" not in response_json:
                raise UnknownResponseError("")
        except requests.RequestException as err:
            logging.error(f"Failed to get site: {str(err)}")
            raise PlejdAPIError(f"Failed to get site: {str(err)}") from err
        except (ValueError, UnknownResponseError) as err:
            logging.error(f"Failed to parse site response:  {str(err)}")
            raise UnknownResponseError(f"Failed to parse site response:  {str(err)}") from err

        return response_json["result"]

    def _get_json_site_from_cache(self) -> dict:
        """Get site from cache.

        Returns
        -------
        dict
            JSON content of the site
        """
        try:
            with open(self._settings.cache_dir + self._settings.cache_file, "r") as file:
                json_site = json.load(file)
            logging.info("Loaded site from cache")
        except (FileNotFoundError, IsADirectoryError, PermissionError, IOError) as err:
            error_message = f"Failed to read cache file: {str(err)}"
            logging.error(error_message)
            raise CacheFileError(error_message) from err
        return json_site

    def store_json_site_to_cache(self, json_site: dict) -> None:
        """Store site to cache.

        Parameters
        ----------
        json_site : dict
            JSON content of the site
        """
        file_path = self._settings.cache_dir + self._settings.cache_file
        try:
            with open(file_path, "w") as file:
                json.dump(json_site, file)
            logging.info(f"Stored site to cache file: {file_path}")
        except (FileNotFoundError, IsADirectoryError, PermissionError, IOError) as err:
            error_message = f"Failed to write cache file: {str(err)}"
            logging.error(error_message)
            raise CacheFileError(error_message) from err

    def _get_devices(self, json_res: dict) -> list[BTDeviceInfo]:
        """Get all devices from Plejd API.

        Parameters
        ----------
        json_res : dict
            JSON content of the site

        Returns
        -------
        list[BTDeviceInfo]
            List of all devices
        """
        device_list = []
        plejd_devices = json_res["plejdDevices"]
        output_address = json_res["outputAddress"]
        device_address = json_res["deviceAddress"]
        output_settings_list = json_res["outputSettings"]
        input_settings_list = json_res["inputSettings"]
        for device in json_res["devices"]:  # Get all necessary plejd device details
            device_id = device["deviceId"]
            device_name = device["title"]
            device_hardware_id = device_address[device_id]

            try:
                device_type = self._get_device_type(device_hardware_id)
            except UnsupportedDeviceTypeError as err:
                logging.warning(f"Failed to get device type for {device_name}: {str(err)}")
                continue

            devices = list(filter(lambda x: x["deviceId"] == device["deviceId"], plejd_devices))[:1]
            if len(devices) > 0:
                device_firmware_version = devices[0]["firmware"]["version"]
            else:
                logging.warning(f"Could not determine FW version for device: {device_name}")
                device_firmware_version = "xxx"

            output_settings = list(
                filter(
                    lambda x: x["deviceParseId"] == device["objectId"],
                    output_settings_list,
                )
            )[:1]
            input_settings = list(
                filter(lambda x: x["deviceId"] == device["deviceId"], input_settings_list)
            )

            if len(output_settings) > 0:  # It's an output device
                if device_id not in output_address:
                    logging.warning(
                        f"Device: {device_name} does not exist as output address, skipping device"
                    )
                    continue

                if device["traits"] == plejd_mqtt_ha.constants.PlejdTraits.NO_LOAD.value:
                    logging.warning(
                        f"No load settings found for output device: {device_name}, skipping device"
                    )
                    continue

                device_index = output_settings[0][
                    "output"
                ]  # TODO is this really the correct index??
                device_ble_address = output_address[device_id][str(device_index)]
                # Append output index to device id for uniqueness
                device_unique_id = device_id + f"_{device_index}"
            elif len(input_settings) > 0:  # It's an input device
                if device_id not in device_address:
                    logging.warning(
                        f"Device: {device_name} does not exist as device address, skipping"
                    )
                    continue

                device_ble_address = device_address[device_id]
                for input_setting in input_settings:
                    if not device_type.broadcast_clicks:
                        logging.info(
                            f"Input device: {device_name} does not broadcast clicks, skipping"
                        )
                        continue

                    device_index = input_setting["input"]  # TODO is this really the correct index??
                    # Append input index to device id for uniqueness
                    device_unique_id = device_id + f"_{device_index}"
            else:
                logging.warning(
                    f"Device: {device_name} is neither output nor input device, skipping"
                )
                continue

            # Parse type and create device info
            if device_type.device_category == plejd_mqtt_ha.constants.PlejdType.LIGHT.value:
                plejd_device = BTLightInfo(
                    model=device_type.name,
                    type=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                    device_id=device_id,
                    unique_id=device_unique_id,
                    name=device_name,
                    hardware_id=device_hardware_id,
                    index=device_index,
                    ble_address=device_ble_address,
                    category=device_type.device_category,
                    firmware_version=device_firmware_version,
                    brightness=device_type.dimmable,
                )
            elif device_type.device_category == plejd_mqtt_ha.constants.PlejdType.SWITCH.value:
                # TODO create
                logging.warning(
                    f"Usnupported device category {plejd_mqtt_ha.constants.PlejdType.SWITCH.value}"
                )
                continue
            elif device_type.device_category == plejd_mqtt_ha.constants.PlejdType.SENSOR.value:
                # TODO
                logging.warning(
                    f"Usnupported device category {plejd_mqtt_ha.constants.PlejdType.SENSOR.value}"
                )
                continue
            elif (
                device_type.device_category
                == plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value
            ):
                # TODO
                logging.warning(
                    "Usnupported device category "
                    f"{plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value}"
                )
                continue
            else:
                continue

            device_list.append(plejd_device)

        return device_list

    def _get_device_type(self, hardware_id: int) -> PlejdDeviceType:
        # Get type of device by hardware id
        if hardware_id in {1, 11, 14}:
            return self.PlejdDeviceType(
                name="DIM-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=True,
                broadcast_clicks=False,
            )
        if hardware_id in {2, 15}:
            return self.PlejdDeviceType(
                name="DIM-02",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=True,
                broadcast_clicks=False,
            )
        if hardware_id == 3:
            return self.PlejdDeviceType(
                name="CTR-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 4:
            return self.PlejdDeviceType(
                name="GWY-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.SENSOR.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 5:
            return self.PlejdDeviceType(
                name="LED-10",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=True,
                broadcast_clicks=False,
            )
        if hardware_id == 6:
            return self.PlejdDeviceType(
                name="WPH-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value,
                dimmable=False,
                broadcast_clicks=True,
            )
        if hardware_id == 7:
            return self.PlejdDeviceType(
                name="REL-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.SWITCH.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 8:
            return self.PlejdDeviceType(
                name="SPR-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.SWITCH.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 9:
            return self.PlejdDeviceType(
                name="WRT-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 10:
            return self.PlejdDeviceType(
                name="WRT-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value,
                dimmable=False,
                broadcast_clicks=True,
            )
        if hardware_id == 12:
            return self.PlejdDeviceType(
                name="DAL-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 13:
            return self.PlejdDeviceType(
                name="Generic",
                device_category=plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value,
                dimmable=False,
                broadcast_clicks=True,
            )
        if hardware_id == 16:
            return self.PlejdDeviceType(
                name="-unknown-",
                device_category=plejd_mqtt_ha.constants.PlejdType.DEVICE_TRIGGER.value,
                dimmable=False,
                broadcast_clicks=True,
            )
        if hardware_id == 17:
            return self.PlejdDeviceType(
                name="REL-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.SWITCH.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 18:
            return self.PlejdDeviceType(
                name="REL-02",
                device_category=plejd_mqtt_ha.constants.PlejdType.SWITCH.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 19:
            return self.PlejdDeviceType(
                name="-unknown-",
                device_category=plejd_mqtt_ha.constants.PlejdType.LIGHT.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        if hardware_id == 20:
            return self.PlejdDeviceType(
                name="SPR-01",
                device_category=plejd_mqtt_ha.constants.PlejdType.SWITCH.value,
                dimmable=False,
                broadcast_clicks=False,
            )
        error_message = f"Failed to get device type for device id {hardware_id}"
        logging.error(error_message)
        raise UnsupportedDeviceTypeError(error_message)
