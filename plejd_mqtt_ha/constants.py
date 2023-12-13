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

"""Project wide constants."""

####################################################################################################
# Plejd API
####################################################################################################

from enum import Enum

API_APP_ID = "zHtVqXt8k4yFyk2QGmgp48D9xZr2G94xWYnF4dak"
API_BASE_URL = "https://cloud.plejd.com/parse/"
API_LOGIN_URL = "login"
API_SITE_LIST_URL = "functions/getSiteList"
API_SITE_DETAILS_URL = "functions/getSiteById"
API_DEFAULT_SITE_NAME = None

####################################################################################################
# Plejd BLE
####################################################################################################

# Plejd service
BLE_UUID_SUFFIX = "6085-4726-be45-040c957391b5"
PLEJD_SERVICE = "31ba0001-" + BLE_UUID_SUFFIX


class PlejdCharacteristic(str, Enum):
    """Plejd characteristic UIIDs."""

    DATA_UUID = "31ba0004-" + BLE_UUID_SUFFIX
    LAST_DATA_UUID = "31ba0005-" + BLE_UUID_SUFFIX
    AUTH_UUID = "31ba0009-" + BLE_UUID_SUFFIX
    PING_UUID = "31ba000a-" + BLE_UUID_SUFFIX


class PlejdCommand(int, Enum):
    """Plejd BLE commands."""

    BLE_CMD_DIM_CHANGE = 0x00C8
    BLE_CMD_DIM2_CHANGE = 0x0098
    BLE_CMD_STATE_CHANGE = 0x0097
    BLE_CMD_SCENE_TRIG = 0x0021
    BLE_CMD_TIME_UPDATE = 0x001B
    BLE_CMD_REMOTE_CLICK = 0x0016


class PlejdLightAction(str, Enum):
    """BLE payload for possible actions on a light."""

    BLE_DEVICE_ON = "01"
    BLE_DEVICE_OFF = "00"
    BLE_DEVICE_DIM = "01"


class PlejdResponse(int, Enum):
    """Possible Plejd device responses."""

    BLE_REQUEST_NO_RESPONSE = 0x0110
    BLE_REQUEST_RESPONSE = 0x0102


####################################################################################################
# Plejd MISC
####################################################################################################


# Traits
class PlejdTraits(int, Enum):
    """Plejd device traits."""

    NO_LOAD = 0
    NON_DIMMABLE = 9  # TODO: Not used yet
    DIMMABLE = 11  # TODO: Not used yet


# Device types
class PlejdType(str, Enum):
    """Plejd device types."""

    SWITCH = "switch"
    LIGHT = "light"
    SENSOR = "sensor"
    DEVICE_TRIGGER = "device_automation"
    UNKNOWN = "unknown"


LOG_FILE_SIZE = 1024 * 1024 * 1  # 1 MB
LOG_FILE_COUNT = 3
