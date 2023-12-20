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

    @validator("cache_policy")
    def cache_policy_is_valid(cls, v):
        """Validate cache policy."""
        if v not in ["NO_CACHE", "FIRST_CACHE", "NEEDED_CACHE"]:
            raise ValueError("Invalid cache policy")
        return v


class MQTT(BaseModel):
    """Settings related to MQTT broker.

    Settings are equivalent to the ones used by ha-mqtt-discovery. See
    https://github.com/unixorn/ha-mqtt-discoverable
    """

    host: str = "localhost"
    """MQTT broker host"""
    port: Optional[int] = 1883
    """MQTT broker port"""
    username: Optional[str] = None
    """MQTT broker username"""
    password: Optional[str] = None
    """MQTT broker password"""
    client_name: Optional[str] = None
    """MQTT client name"""
    use_tls: Optional[bool] = False
    """Whether or not to use TLS"""
    tls_key: Optional[str] = None
    """TLS key file"""
    tls_certfile: Optional[str] = None
    """TLS certificate file"""
    tls_ca_cert: Optional[str] = None
    """TLS CA certificate file"""

    discovery_prefix: str = "homeassistant"
    """The root of the topic tree where HA is listening for messages"""
    state_prefix: str = "hmd"
    """The root of the topic tree ha-mqtt-discovery publishes its state messages"""


class BLE(BaseModel):
    """Settings related to BLE."""

    adapter: Optional[str] = None
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

    time_update_interval: float = 60.0 * 60.0  # 1 hour
    """Interval in seconds between updating Plejd time"""
    time_update_threshold: float = 10.0
    """Time difference in seconds between Plejd time and local time before updating Plejd time"""
    time_use_sys_time: bool = True
    """Whether or not to use system time instead of time from an NTP server"""
    timezone: Optional[str] = None
    """Timezone to use for time updates, if not set system timezone will be used.
    Should be in the form of e.g. "Europe/Stockholm"
    """
    ntp_server: Optional[str] = "pool.ntp.org"
    """NTP server to use for time updates, if not set system time will be used"""
