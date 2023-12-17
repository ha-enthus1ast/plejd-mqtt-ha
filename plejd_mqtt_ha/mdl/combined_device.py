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
from ha_mqtt_discoverable.sensors import (
    DeviceTrigger,
    DeviceTriggerInfo,
    Light,
    LightInfo,
    Subscriber,
)
from paho.mqtt.client import Client, MQTTMessage
from plejd_mqtt_ha.bt_client import BTClient, PlejdNotConnectedError
from plejd_mqtt_ha.mdl.bt_data_type import BTDeviceTriggerData, BTLightData
from plejd_mqtt_ha.mdl.bt_device import BTDevice, BTDeviceTrigger, BTLight
from plejd_mqtt_ha.mdl.bt_device_info import (
    BTDeviceInfo,
    BTDeviceTriggerInfo,
    BTLightInfo,
)
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
        self._mqtt_entities = None
        self._bt_device: Optional[BTDevice] = None

    async def start(self) -> None:
        """Start the combined device.

        This will register it with HA and connect it to the physical device.
        """
        try:
            self._mqtt_entities = self._create_mqtt_device()
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

    def _create_mqtt_device(self) -> list[Subscriber[PlejdDeviceTypeT]]:
        """Create an MQTT device, shall be overriden in all subclasses.

        If a callbac is needed, use the _mqtt_callback function.

        Returns
        -------
        list[Subscriber[PlejdDeviceTypeT]]
            List of MQTT entities

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

    def _create_mqtt_device(self) -> list[Subscriber[BTLightInfo]]:
        # Override
        mqtt_device_info = DeviceInfo(
            name=self._device_info.name,
            identifiers=self._device_info.unique_id,
            manufacturer="Plejd",
            model=self._device_info.model,
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
        light = Light(settings=settings, command_callback=self._mqtt_callback)
        light.off()  # Publish initial state to register with HA
        return [light]

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
        mqtt_entity = self._mqtt_entities[0]
        if not self._bt_device:
            logging.info(f"BT device {self._device_info.name} not created yet")
            return
        if "brightness" in payload:
            if asyncio.run_coroutine_threadsafe(
                self._bt_device.brightness(payload["brightness"]), loop=self._event_loop
            ):
                mqtt_entity.brightness(payload["brightness"])  # TODO generics?
        elif "state" in payload:
            if payload["state"] == "ON":
                if asyncio.run_coroutine_threadsafe(self._bt_device.on(), loop=self._event_loop):
                    mqtt_entity.on()
            else:
                if asyncio.run_coroutine_threadsafe(self._bt_device.off(), loop=self._event_loop):
                    mqtt_entity.off()
        else:
            logging.warning(f"Unknown payload {payload}")

    def _bt_callback(self, light_response: BTLightData) -> None:
        # Override
        if not light_response:
            return

        if not self._mqtt_entities:
            logging.info(f"MQTT device {self._device_info.name} not created yet")
            return

        mqtt_entity = self._mqtt_entities[0]  # Only one can exist

        if light_response.state:
            mqtt_entity.brightness(light_response.brightness)
        else:
            mqtt_entity.off()


class CombinedDeviceTrigger(CombinedDevice[BTDeviceTriggerInfo]):
    """A combined Plejd BT and MQTT device trigger."""

    def _create_mqtt_device(self) -> list[Subscriber[DeviceTriggerInfo]]:
        # Override
        mqtt_device_info = DeviceInfo(
            name=self._device_info.name,
            identifiers=self._device_info.unique_id,
            manufacturer="Plejd",  # TODO: HC for now
            model=self._device_info.model,
        )

        # If first button is double sided, all are
        double_sided = self._device_info.buttons[0]["double_sided"]

        mqtt_entities = []
        for index, button in enumerate(self._device_info.buttons):
            # If a double sided button, we need to create two triggers ie button_0 and button_1
            # If not, we only need to create one trigger ie button
            subtype = "button_" + str(index % 2) if double_sided else "button"

            mqtt_device_trigger_info = DeviceTriggerInfo(
                name=subtype,
                unique_id=self._device_info.unique_id + "_" + str(index % 2),
                type=button["type"],
                subtype=subtype,
                device=mqtt_device_info,
            )

            settings = Settings(mqtt=self._settings.mqtt, entity=mqtt_device_trigger_info)
            device_trigger = DeviceTrigger(settings=settings)
            device_trigger.trigger()
            mqtt_entities.append(device_trigger)
            logging.debug(
                f"Created MQTT device trigger {mqtt_device_trigger_info.name} with unique id "
                f"{mqtt_device_trigger_info.unique_id}. The type of the device trigger is "
                f"{mqtt_device_trigger_info.type}. It belongs to device {self._device_info.name}"
            )
        return mqtt_entities

    async def _create_bt_device(self) -> BTDevice:
        # Override
        bt_device_trigger = BTDeviceTrigger(
            bt_client=self._plejd_bt_client, device_info=self._device_info
        )

        logging.debug(
            f"Created BT device {self._device_info.name} with unique id "
            f"{self._device_info.unique_id} at BLE address {self._device_info.ble_address}."
        )

        try:
            await bt_device_trigger.subscribe(self._bt_callback)
        except PlejdNotConnectedError as err:
            error_message = f"Failed to subscribe to BT data for device {self._device_info.name}"
            logging.error(error_message)
            raise BTDeviceError(error_message) from err

        return bt_device_trigger

    def _bt_callback(self, device_trigger_response: BTDeviceTriggerData) -> None:
        # Override
        if not device_trigger_response:
            return

        if not self._mqtt_entities:
            logging.warning(f"MQTT device {self._device_info.name} not created yet")
            return

        # Figure out which entity to trigger
        unique_id = self._device_info.unique_id + "_" + str(device_trigger_response.input)
        for entity in self._mqtt_entities:
            if entity._entity.unique_id == unique_id:
                logging.debug(
                    f"Triggering {entity._entity.name} with type {entity._entity.type} and "
                    f"{unique_id}, belonging to device {self._device_info.name}"
                )
                entity.trigger()
                return

        logging.warning(
            f"No entity with unique_id {unique_id} found for device "
            f"{self._device_info.name} with unique_id {self._device_info.unique_id}"
        )
