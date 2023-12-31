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

"""Plejd bluetooth device.

All new BT devices should add a new class here, inheriting from BTDevice.
"""

import logging
from typing import Callable, Generic, Optional, TypeVar

from plejd_mqtt_ha import constants
from plejd_mqtt_ha.bt_client import (
    BTClient,
    PlejdBluetoothError,
    PlejdNotConnectedError,
    PlejdTimeoutError,
)
from plejd_mqtt_ha.mdl.bt_data_type import (
    BTData,
    BTDeviceTriggerData,
    BTLightData,
    BTSwitchData,
)
from plejd_mqtt_ha.mdl.bt_device_info import (
    BTDeviceInfo,
    BTDeviceTriggerInfo,
    BTLightInfo,
    BTSwitchInfo,
)

PlejdDeviceTypeT = TypeVar("PlejdDeviceTypeT", bound=BTDeviceInfo)


class BTDevice(Generic[PlejdDeviceTypeT]):
    """Plejd bluetooth device super class."""

    def __init__(self, bt_client: BTClient, device_info: PlejdDeviceTypeT) -> None:
        """Initialize the BTDevice instance.

        Parameters
        ----------
        bt_client : BTClient
            BTClient instance to use for communication
        device_info : PlejdDeviceTypeT
            Device info for the device
        """
        self._device_info = device_info
        self._plejd_bt_client = bt_client

    async def subscribe(self, callback: Callable[[BTData], None]) -> bool:
        """Subscribe to changes for the device.

        Parameters
        ----------
        callback : Callable[[PlejdResponseType], None]
            Callback to be invoked when data is received

        Returns
        -------
        bool
            Boolean status of the operation
        """

        def _proxy_callback(decrypted_data: bytearray) -> None:
            callback(self._decode_response(decrypted_data))  # return parsed data

        return await self._plejd_bt_client.subscribe_last_data(
            self._device_info.ble_address, _proxy_callback
        )

    def _decode_response(self, decrypted_data: bytearray) -> Optional[BTData]:
        """Device specific decoding to be implemented by subclass, ie device class.

        Parameters
        ----------
        decrypted_data : bytearray
            Decrypted data coming from Plejd device

        Raises
        ------
        NotImplementedError
            In case it's not implemented in subclass but a callback is provided
        """
        raise NotImplementedError


class BTSwitch(BTDevice[BTSwitchInfo]):
    """Plejd bluetooth switch."""

    async def on(self) -> bool:
        """Turn on a physical Plejd Switch.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logging.debug(f"Turning on device {self._device_info.name}")
        try:
            await self._plejd_bt_client.send_command(
                self._device_info.ble_address,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                constants.PlejdAction.BLE_DEVICE_ON,
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE,
            )
        except PlejdNotConnectedError as err:
            logging.warning(
                f"Device {self._device_info.name} is not connected, cannot turn on."
                f"Error: {str(err)}"
            )
            return False
        except (PlejdBluetoothError, PlejdTimeoutError) as err:
            logging.warning(
                f"Failed to turn on device {self._device_info.name}, due to bluetooth a error."
                f"Error: {str(err)}"
            )
            return False

        return True

    async def off(self) -> bool:
        """Turn off a physical Plejd Switch.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logging.debug(f"Turning off device {self._device_info.name}")

        try:
            await self._plejd_bt_client.send_command(
                self._device_info.ble_address,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                constants.PlejdAction.BLE_DEVICE_OFF,
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE,
            )
        except PlejdNotConnectedError as err:
            logging.warning(
                f"Device {self._device_info.name} is not connected, cannot turn on."
                f"Error: {str(err)}"
            )
            return False
        except (PlejdBluetoothError, PlejdTimeoutError) as err:
            logging.warning(
                f"Failed to turn on device {self._device_info.name}, due to bluetooth a error."
                f"Error: {str(err)}"
            )
            return False

        return True

    def _decode_response(self, decrypted_data: bytearray) -> Optional[BTDeviceTriggerData]:
        # Overriden
        command = int.from_bytes(bytes=decrypted_data[3:5], byteorder="big")

        if command == constants.PlejdCommand.BLE_CMD_TIME_UPDATE:  # Time update handled elsewhere
            logging.debug("Ignoring time update in switch")
            return None

        if command not in self._device_info.supported_commands:
            logging.debug(
                f"Command {command} not supported for device category {self._device_info.category}"
            )
            return None

        state = decrypted_data[5] if len(decrypted_data) > 5 else 0

        response = BTSwitchData(raw_data=decrypted_data, state=bool(state))

        return response


class BTLight(BTDevice[BTLightInfo]):
    """Plejd bluetooth light device."""

    async def on(self) -> bool:
        """Turn on a physical Plejd Light.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logging.debug(f"Turning on device {self._device_info.name}")
        try:
            await self._plejd_bt_client.send_command(
                self._device_info.ble_address,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                constants.PlejdAction.BLE_DEVICE_ON,
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE,
            )
        except PlejdNotConnectedError as err:
            logging.warning(
                f"Device {self._device_info.name} is not connected, cannot turn on."
                f"Error: {str(err)}"
            )
            return False
        except (PlejdBluetoothError, PlejdTimeoutError) as err:
            logging.warning(
                f"Failed to turn on device {self._device_info.name}, due to bluetooth a error."
                f"Error: {str(err)}"
            )
            return False

        return True

    async def off(self) -> bool:
        """Turn off a physical Plejd Light.

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logging.debug(f"Turning off device {self._device_info.name}")

        try:
            await self._plejd_bt_client.send_command(
                self._device_info.ble_address,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                constants.PlejdAction.BLE_DEVICE_OFF,
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE,
            )
        except PlejdNotConnectedError as err:
            logging.warning(
                f"Device {self._device_info.name} is not connected, cannot turn on."
                f"Error: {str(err)}"
            )
            return False
        except (PlejdBluetoothError, PlejdTimeoutError) as err:
            logging.warning(
                f"Failed to turn on device {self._device_info.name}, due to bluetooth a error."
                f"Error: {str(err)}"
            )
            return False

        return True

    async def brightness(self, brightness: int) -> bool:
        """Set brightness of a Plejd Light.

        Parameters
        ----------
        brightness : int
            Brightness to set, 0-255

        Returns
        -------
        bool
            True if successful, False otherwise
        """
        logging.debug(f"Setting brightness of device {self._device_info.name}")

        if not self._device_info.brightness:
            raise RuntimeError(
                f"Device {self._device_info.name} does not support setting brightness"
            )

        pad = "0" if brightness <= 0xF else ""
        s_brightness = brightness << 8 | brightness
        data = constants.PlejdAction.BLE_DEVICE_DIM + pad + f"{s_brightness:X}"
        try:
            await self._plejd_bt_client.send_command(
                self._device_info.ble_address,
                constants.PlejdCommand.BLE_CMD_DIM2_CHANGE,
                data,
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE,
            )
        except PlejdNotConnectedError as err:
            logging.warning(
                f"Device {self._device_info.name} is not connected, cannot turn on."
                f"Error: {str(err)}"
            )
            return False
        except (PlejdBluetoothError, PlejdTimeoutError) as err:
            logging.warning(
                f"Failed to turn on device {self._device_info.name}, due to bluetooth a error."
                f"Error: {str(err)}"
            )
            return False

        return True

    def _decode_response(self, decrypted_data: bytearray) -> Optional[BTLightData]:
        # Overriden
        command = int.from_bytes(bytes=decrypted_data[3:5], byteorder="big")

        if command == constants.PlejdCommand.BLE_CMD_TIME_UPDATE:
            logging.debug("Ignoring time update in light")
            return None

        if command not in self._device_info.supported_commands:
            logging.error(
                f"Command {command} not supported for device category {self._device_info.category}"
            )

        state = decrypted_data[5] if len(decrypted_data) > 5 else 0
        brightness = decrypted_data[7] if len(decrypted_data) > 7 else 0

        brightness = int(brightness)
        state = bool(state)
        response = BTLightData(
            raw_data=decrypted_data,
            state=state,
            brightness=brightness,
        )
        return response


class BTDeviceTrigger(BTDevice[BTDeviceTriggerInfo]):
    """Plejd bluetooth device trigger.

    This device only listens to button presses, and does not support any commands.
    """

    def _decode_response(self, decrypted_data: bytearray) -> Optional[BTDeviceTriggerData]:
        # Overriden
        command = int.from_bytes(bytes=decrypted_data[3:5], byteorder="big")

        if command == constants.PlejdCommand.BLE_CMD_TIME_UPDATE:
            logging.debug("Ignoring time update in device trigger")
            return None

        if command not in self._device_info.supported_commands:
            logging.debug(
                f"Command {command} not supported for device category {self._device_info.category}"
            )
            return None

        if len(decrypted_data) < 8:
            logging.debug(
                f"Device trigger {self._device_info.name} received too short data, ignoring"
            )
            return None

        input = decrypted_data[6]  # Which input is triggered

        response = BTDeviceTriggerData(
            raw_data=decrypted_data,
            input=int(input),
        )

        return response
