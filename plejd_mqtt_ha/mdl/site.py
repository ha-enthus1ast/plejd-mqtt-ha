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

"""Type to hold parsed data from plejd cloud, containing information about an entire site."""

from plejd_mqtt_ha.mdl.bt_device_info import BTDeviceInfo
from pydantic import BaseModel


class PlejdSite(BaseModel):
    """Holds important data related to a Plejd site."""

    name: str
    """Name of the site"""
    site_id: str
    """Identity of the site"""
    crypto_key: str
    """Crypto key used to authenticate against the plejd mesh"""
    devices: list[BTDeviceInfo]
    """List of devices belonging to the site"""
