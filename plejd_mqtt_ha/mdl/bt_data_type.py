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

"""Type to hold parsed data coming from a plejd device.

All new BT devices should add a new class here, inheriting from BTData.
"""

from pydantic import BaseModel


class BTData(BaseModel):
    """Type to hold parsed data coming from a plejd device."""

    raw_data: bytearray
    """Raw, decrypted data from the Plejd device
    """

    class Config:
        """Pydantic BaseModel configuration."""

        arbitrary_types_allowed = True  # Allow for bytearray


class BTLightData(BTData):
    """Parsed data type coming from a plejd light."""

    state: bool
    """State of the light, True = light is ON
    """
    brightness: int
    """Brightness of the Plejd light
    """


class BTDeviceTriggerData(BTData):
    """Parsed data type coming from a plejd light."""

    input: int
    """Which input is triggered
    """
