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

"""Main module."""

import os
import sys

from plejd_mqtt_ha import plejd


def main():
    """Entry point of the application."""

    # Load environment variables
    log_level = os.getenv("LOG_LEVEL", "ERROR").upper()
    config = os.getenv("CONFIG", "/config/settings.yaml")
    log_file = os.getenv("LOG_FILE", "/config/logs/plejd.log")

    sys.exit(plejd.start(config=config, log_level=log_level, log_file=log_file))


if __name__ == "__main__":
    main()
