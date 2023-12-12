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

"""Settings module for Plejd MQTT HA.

Settings are loaded from a YAML file, which is passed as a command line argument to the program.
"""


import os
from typing import Optional

from pydantic import BaseModel, validator


class API(BaseModel):
    """Settings related to Plejd API."""

    user: str
    """Plejd user name (email)"""
    password: str
    """Password of the plejd user"""
    site: Optional[str] = None
    """Name of the plejd site to use, default is the first in the accounts list"""
    timeout: float = 10.0
    """Timeout to reach Plejd API"""
    cache_policy: str = "FIRST_CACHE"
    """
    Cache policy to use. Can be one of the following:
    - "NO_CACHE": Does not use cache.
    - "FIRST_CACHE": Caches the plejd site on first run, then uses cache.
    - "NEEDED_CACHE": Uses cached site only when network is not available.
    """
    cache_dir: str = "/config/"  # TODO: Does not belong here
    """Directory to store cached site, not used if cache_policy is set to NO_CACHE"""
    cache_file: str = "site.json"
    """File name for cached site, not used if cache_policy is set to NO_CACHE"""

    @validator("cache_policy")
    def cache_policy_is_valid(cls, v):
        """Validate cache policy."""
        if v not in ["NO_CACHE", "FIRST_CACHE", "NEEDED_CACHE"]:
            raise ValueError("Invalid cache policy")
        return v


class MQTT(BaseModel):
    """Settings related to MQTT broker."""

    host: str = "localhost"
    """Address of the host MQTT broker"""
    port: int = 1883
    """Port of the MQTT host"""
    user: Optional[str] = None
    """MQTT user name"""
    password: Optional[str] = None
    """Password of the MQTT user"""
    ha_discovery_prefix: str = "homeassistant"
    """Home assistant discovery prefix"""


class BLE(BaseModel):
    """Settings related to BLE."""

    adapter: Optional[str] = None  # TODO: implement
    """If a specific bluetooth adapter is to be used"""
    preferred_device: Optional[str] = None  # TODO: implement
    """If a specific Plejd device is to be used as mesh ingress point, if not set the device with
    the strongest signal will be used. Not recommended to use this setting"""
    scan_time: float = 10.0
    """Time to scan for plejd bluetooth devices"""
    retries: int = 10
    """Number of times to try and reconnect to Plejd mesh"""
    time_retries: float = 10.0
    """Time between retries"""


class PlejdSettings(BaseModel):
    """Single class containing all settings."""

    api: API
    """Plejd API settings"""
    mqtt: MQTT = MQTT()
    """MQTT settings"""
    ble: BLE = BLE()
    """BLE settings"""

    health_check: bool = True
    """Enable health check"""
    health_check_interval: float = 60.0
    """Interval in seconds between writing health check files"""
    health_check_dir: str = os.path.expanduser("~/.plejd/")
    """Directory to store health check files"""
    health_check_bt_file: str = "bluetooth"
    """File name for bluetooth health check"""
    health_check_mqtt_file: str = "mqtt"
    """File name for MQTT health check"""
    health_check_hearbeat_file: str = "heartbeat"
    """File name for heartbeat file"""
