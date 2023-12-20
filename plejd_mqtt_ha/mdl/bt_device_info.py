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

"""Type to hold information about a Plejd device.

All new BT devices should add a new class here, inheriting from BTDeviceInfo.
"""

from typing import Optional

from plejd_mqtt_ha import constants
from pydantic import BaseModel


class BTDeviceInfo(BaseModel):
    """Base class that defines device information common to all plejd devices."""

    category: str
    """Type of device category, ie light etc"""
    supported_commands: Optional[list] = None
    """List of Plejd BLE commands to listen to, device type specific"""

    model: str
    """Model of the device"""
    device_id: str
    """Identity of the device, as stated in the Plejd API"""
    unique_id: str
    """Unique identity of the device, required by HA"""
    name: str
    """Name of the device"""
    hardware_id: str
    """Adress of the device within the Plejd mesh"""
    index: int
    """Index of the entity belonging to the device"""
    ble_address: int
    """BLE address of the device"""
    firmware_version: Optional[str] = None
    """Firmware version of the device"""


class BTSwitchInfo(BTDeviceInfo):
    """Information specific to switch devices."""

    category = "switch"
    supported_commands = [
        constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
    ]


class BTLightInfo(BTDeviceInfo):
    """Information specific to light devices."""

    category = "light"
    supported_commands = [
        constants.PlejdCommand.BLE_CMD_DIM2_CHANGE,
        constants.PlejdCommand.BLE_CMD_DIM_CHANGE,
        constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
    ]

    brightness: bool = False
    """Whether or not the light supports setting brightness"""


class BTDeviceTriggerInfo(BTDeviceInfo):
    """Information specific to trigger devices."""

    category = "device_trigger"
    supported_commands = [
        constants.PlejdCommand.BLE_CMD_REMOTE_CLICK,
        constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
        constants.PlejdCommand.BLE_CMD_DIM_CHANGE,
        constants.PlejdCommand.BLE_CMD_DIM2_CHANGE,
    ]

    buttons: list[dict]
    """List of buttons on the device, each button is a dict with the following keys:
    - type: Type of button, ie DirectionUp, DirectionDown etc
    - double_sided: Whether or not the button is double sided
    - input: Input number of the button
    """
