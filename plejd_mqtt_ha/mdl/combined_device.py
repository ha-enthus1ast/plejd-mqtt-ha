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

"""Combined device module, combines a Plejd BT device with an MQTT device.

All new devices should be added here, inheriting from CombinedDevice.
"""

import asyncio
import json
import logging
from typing import Generic, Optional, TypeVar

from ha_mqtt_discoverable import DeviceInfo, Discoverable, Settings
from ha_mqtt_discoverable.sensors import Light, LightInfo, Subscriber
from paho.mqtt.client import Client, MQTTMessage
from plejd_mqtt_ha.bt_client import BTClient, PlejdNotConnectedError
from plejd_mqtt_ha.mdl.bt_data_type import BTLightData
from plejd_mqtt_ha.mdl.bt_device import BTDevice, BTLight
from plejd_mqtt_ha.mdl.bt_device_info import BTDeviceInfo, BTLightInfo
from plejd_mqtt_ha.mdl.settings import PlejdSettings

PlejdDeviceTypeT = TypeVar("PlejdDeviceTypeT", bound=BTDeviceInfo)
MQTTDeviceTypeT = TypeVar("MQTTDeviceTypeT", bound=Discoverable)


class CombinedDeviceError(Exception):
    """Combined device error."""

    def __init__(self, message: str) -> None:
        """Initialize the CombinedDeviceError instance.

        Parameters
        ----------
        message : str
            Error message
        """
        self.message = message
        super().__init__(self.message)


class MQTTDeviceError(CombinedDeviceError):
    """MQTT device error."""

    pass


class BTDeviceError(CombinedDeviceError):
    """MQTT device error."""

    pass


class CombinedDevice(Generic[PlejdDeviceTypeT]):
    """A combined device that connects a Plejd BT device to an MQTT devices."""

    def __init__(
        self,
        bt_client: BTClient,
        settings: PlejdSettings,
        device_info: PlejdDeviceTypeT,
    ) -> None:
        """Initialize the CombinedDevice instance.

        Parameters
        ----------
        bt_client : BTClient
            BTClient instance to use for communication
        settings : PlejdSettings
            Settings for the device
        device_info : PlejdDeviceTypeT
            Device info for the device
        """
        self._device_info = device_info
        self._settings = settings
        self._plejd_bt_client = bt_client
        self._event_loop = asyncio.get_event_loop()
        self._mqtt_device = None
        self._bt_device: Optional[BTDevice] = None

    async def start(self) -> None:
        """Start the combined device.

        This will register it with HA and connect it to the physical device.
        """
        try:
            self._mqtt_device = self._create_mqtt_device()
        except ConnectionError as err:
            error_msg = f"Failed to connect to MQTT broker for {self._device_info.name}"
            logging.error(error_msg)
            raise MQTTDeviceError(error_msg) from err
        except RuntimeError as err:
            error_msg = f"Failed to create MQTT device for {self._device_info.name}"
            logging.error(error_msg)
            raise MQTTDeviceError(error_msg) from err

        try:
            self._bt_device = await self._create_bt_device()
        except BTDeviceError as err:
            error_msg = f"Failed to create BT device for {self._device_info.name}"
            logging.error(error_msg)
            raise BTDeviceError(error_msg) from err

    def _create_mqtt_device(self) -> Subscriber[PlejdDeviceTypeT]:
        """Create an MQTT device, shall be overriden in all subclasses.

        If a callbac is needed, use the _mqtt_callback function.

        Returns
        -------
        Any
            The created MQTT device

        Raises
        ------
        NotImplementedError
            Must be implemented in subclass, otherwise we raise an exception
        """
        raise NotImplementedError

    async def _create_bt_device(self) -> BTDevice:
        """Create a Plejd BT mesh device, shall be overriden in all subclasses.

        Returns
        -------
        Optional[BTDevice]
            The created Plejd BT mesh device

        Raises
        ------
        NotImplementedError
            Must be implemented in subclass, otherwise we raise an exception
        """
        raise NotImplementedError

    def _mqtt_callback(self, client: Client, user_data, message: MQTTMessage) -> None:
        """MQTT device callback, shall be implemented by subclass if an MQTT callback is needed.

        Parameters
        ----------
        client : Client
            MQTT client
        user_data : _type_
            Optional user data
        message : MQTTMessage
            Received MQTT message

        Raises
        ------
        NotImplementedError
            If used and not implemented, raise an exception
        """
        raise NotImplementedError

    def _bt_callback(self, light_response: BTLightData) -> None:
        """Plejd BT mesh device callback, shall be implemented if subclass needs a callback.

        Parameters
        ----------
        light_response : PlejdLightResponse
            Data coming from Plejd BT mesh device

        Raises
        ------
        NotImplementedError
            If used and not implemented, raise an exception
        """
        raise NotImplementedError


# TODO create subclass from device category automatically??? Possible?
class CombinedLight(CombinedDevice[BTLightInfo]):
    """A combined Plejd BT and MQTT light."""

    def _create_mqtt_device(self) -> Subscriber[BTLightInfo]:
        # Override
        mqtt_device_info = DeviceInfo(
            name=self._device_info.name, identifiers=self._device_info.unique_id
        )
        supported_color_modes = None
        if self._device_info.brightness:
            supported_color_modes = ["brightness"]

        mqtt_light_info = LightInfo(
            name=self._device_info.name,
            brightness=self._device_info.brightness,
            color_mode=self._device_info.brightness,
            supported_color_modes=supported_color_modes,
            unique_id=self._device_info.unique_id + "_1",
            device=mqtt_device_info,
        )
        settings = Settings(mqtt=self._settings.mqtt, entity=mqtt_light_info)
        return Light(settings=settings, command_callback=self._mqtt_callback)

    async def _create_bt_device(self) -> BTDevice:
        # Override
        bt_light = BTLight(bt_client=self._plejd_bt_client, device_info=self._device_info)
        logging.info(f"Subscribing to BT device {self._device_info.name}")

        try:
            await bt_light.subscribe(self._bt_callback)
        except PlejdNotConnectedError as err:
            error_message = f"Failed to subscribe to BT data for device {self._device_info.name}"
            logging.error(error_message)
            raise BTDeviceError(error_message) from err

        return bt_light

    def _mqtt_callback(self, client: Client, user_data, message: MQTTMessage) -> None:
        # Override
        payload = json.loads(message.payload.decode())
        if not self._bt_device:
            logging.info(f"BT device {self._device_info.name} not created yet")
            return
        if "brightness" in payload:
            if asyncio.run_coroutine_threadsafe(
                self._bt_device.brightness(payload["brightness"]), loop=self._event_loop
            ):
                self._mqtt_device.brightness(payload["brightness"])  # TODO generics?
        elif "state" in payload:
            if payload["state"] == "ON":
                if asyncio.run_coroutine_threadsafe(self._bt_device.on(), loop=self._event_loop):
                    self._mqtt_device.on()
            else:
                if asyncio.run_coroutine_threadsafe(self._bt_device.off(), loop=self._event_loop):
                    self._mqtt_device.off()
        else:
            logging.warning(f"Unknown payload {payload}")

    def _bt_callback(self, light_response: BTLightData) -> None:
        # Override
        if not self._mqtt_device:
            logging.info(f"MQTT device {self._device_info.name} not created yet")
            return

        if light_response.state:
            self._mqtt_device.brightness(light_response.brightness)
        else:
            self._mqtt_device.off()
