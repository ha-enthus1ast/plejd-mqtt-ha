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

"""Bluetooth client for Plejd mesh.

This module handles the BLE communication with the Plejd mesh. It uses the bleak library to
communicate with the Plejd mesh.
"""

import asyncio
import hashlib
import logging
import struct
from datetime import datetime
from random import randbytes
from typing import Any, Callable, Optional

import bleak
import numpy as np
from bleak import BleakClient
from bleak.exc import BleakDBusError, BleakError
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from plejd_mqtt_ha import constants
from plejd_mqtt_ha.mdl.bt_device_info import BTDeviceInfo
from plejd_mqtt_ha.mdl.settings import PlejdSettings


class PlejdBluetoothError(Exception):
    """Base class for exceptions in this module."""

    def __init__(self, message: str):
        """Initialize exception.

        Parameters
        ----------
        message : str
            Error message
        """
        self.message = message
        super().__init__(self.message)


class PlejdNotConnectedError(PlejdBluetoothError):
    """Exception raised for errors if using a Plejd Bluetooth connection when not connected."""

    pass


class PlejdTimeoutError(PlejdBluetoothError):
    """Exception raised for errors when a timeout occurs in Plejd Bluetooth connection."""

    pass


class UnsupportedCharacteristicError(PlejdBluetoothError):
    """Exception raised for errors when trying to use an unsupported characteristic."""

    pass


class UnsupportedCommandError(PlejdBluetoothError):
    """Exception raised for errors when trying to use an unknown command."""

    pass


class BTClient:
    """
    Plejd bluetooth handler. Connect and interact with the physical devices in your plejd mesh.

    BLE connectivity is handled by SimpleBLE library and its python bindings SimplePYBLE
    """

    def __init__(self, crypto_key: str, settings: PlejdSettings):
        """Initialize the BTClient instance.

        Parameters
        ----------
        crypto_key : str
            Crypto key to use for encryption/decryption of data to/from Plejd mesh
        settings : PlejdSettings
            Settings for the Plejd mesh
        """
        self._client: Optional[BleakClient] = None
        self._disconnect = False
        self._settings = settings
        self._crypto_key = crypto_key
        self._callbacks: dict = {}
        self._crypto_key = self._crypto_key.replace("-", "")
        self._crypto_key = bytes.fromhex(self._crypto_key)

    async def _stay_connected_loop(self) -> None:
        async def heartbeat():
            while not self._disconnect:
                retries = 0

                while retries < self._settings.ble.retries:
                    await asyncio.sleep(self._settings.ble.time_retries)

                    if not self.is_connected():
                        await self._connect()
                        retries += 1
                        continue
                    else:
                        if not await self.ping():
                            retries += 1
                            continue

                if retries >= self._settings.ble.retries:
                    logging.warning("Hearbeat timeout")

        await heartbeat()

    async def connect(self, stay_connected: bool) -> bool:
        """Connect to plejd mesh.

        Parameters
        ----------
        stay_connected : bool
            If True, makes sure user stays conneted as a background task

        Returns
        -------
        bool
            True if connection was successful
        """
        logging.info("Connecting to plejd mesh")
        if not self.is_connected():
            if not await self._connect():
                return False

        logging.info("Connected to plejd mesh")
        if stay_connected:
            event_loop = asyncio.get_event_loop()
            event_loop.create_task(self._stay_connected_loop())

        return True

    async def disconnect(self) -> bool:
        """Disconnect from plejd mesh.

        Returns
        -------
        bool
            True if disconnect was successful
        """
        self._disconnect = True
        if self._client and self.is_connected():
            return await self._client.disconnect()

        return True

    def is_connected(self) -> bool:
        """Check if connected to plejd mesh.

        Returns
        -------
        bool
            True if connected to Plejd mesh
        """
        return self._client is not None and self._client.is_connected

    async def send_command(
        self,
        ble_address: int,
        command: int,
        data: str,
        response_type: int,
    ) -> None:
        """Send command to Plejd BLE device.

        Parameters
        ----------
        ble_address : int
            Address of the device to send command to
        command : int
            Command to send
        data : str
            Data to send
        response_type : int
            Response type
        """
        if not self.is_connected():
            error_message = "Trying to send command when not connected to Plejd mesh"
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        try:
            constants.PlejdCommand(command)
        except ValueError as err:
            error_message = f"Trying to send unknown command {command}"
            logging.error(error_message)
            raise UnsupportedCommandError(error_message) from err

        payload = self._get_cmd_payload(ble_address, command, data, response_type)
        encoded_address = self._encode_address(self._client.address)
        encoded_data = self._encrypt_decrypt_data(self._crypto_key, encoded_address, payload)

        try:
            await self._write_request(constants.PlejdCharacteristic.DATA_UUID.value, encoded_data)
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            logging.error(f"Caught an exception when calling _write_request: {str(err)}")
            raise

    async def subscribe_last_data(
        self, ble_address: int, callback: Callable[[bytearray], Any]
    ) -> None:
        """Subscribe to last data received from the mesh.

        Parameters
        ----------
        ble_address : int
            Address of the device to listen to
        callback : Callable[[bytearray],Any]
            Callback function that shall be invoked on data received by the mesh
        """
        if not self.is_connected():
            error_message = "Trying to subscribe to last data when not connected to Plejd mesh"
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        self._callbacks.update({ble_address: callback})

        def _proxy_callback(_, data: bytearray) -> None:
            if not self._client:
                return
            encoded_address = self._encode_address(self._client.address)
            decrypted_data = self._encrypt_decrypt_data(self._crypto_key, encoded_address, data)
            # Since it is a mesh one client handles all subscriptions and we need to dispatch to
            # the correct device
            sender_addr = decrypted_data[0]  # Address of the device that sent data in the mesh
            if sender_addr not in self._callbacks:
                logging.warning(
                    f"Received data from device address {sender_addr} but found no registered"
                    "callback"
                )
                return
            self._callbacks[sender_addr](bytearray(decrypted_data))  # Sender callback

        await self._client.start_notify(
            constants.PlejdCharacteristic.LAST_DATA_UUID.value, _proxy_callback
        )

    async def ping(self) -> bool:
        """Ping plejd mesh to check if it is online.

        Returns
        -------
        bool
            True if ping was successful
        """
        ping_data = randbytes(1)  # any arbitrary payload can be used

        try:
            await self._write_request(constants.PlejdCharacteristic.PING_UUID.value, ping_data)
            pong_data = await self._read_request(constants.PlejdCharacteristic.PING_UUID.value)
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            logging.info(f"Ping operation failed: {str(err)}")
            return False

        if pong_data == bytearray() or not ((ping_data[0] + 1) & 0xFF) == pong_data[0]:
            return False

        return True

    async def get_last_data(self) -> bytes:
        """
        Retrieve last data from plejd mesh. Can for example be used to extract plejd time.

        Returns
        -------
        bytes
            Last data payload
        """
        if not self.is_connected():
            error_message = "Trying to get last data when not connected to Plejd mesh"
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        try:
            encrypted_data = await self._read_request(constants.PlejdCharacteristic.DATA_UUID.value)
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            logging.error(f"Caught an exception when calling _read_request: {str(err)}")
            raise

        encoded_address = self._encode_address(self._client.address)
        return self._encrypt_decrypt_data(self._crypto_key, encoded_address, encrypted_data)

    async def get_plejd_time(self, plejd_device: BTDeviceInfo) -> Optional[datetime]:
        """Request time from plejd mesh.

        Parameters
        ----------
        plejd_device : PlejdDevice
            Plejd device to get time from, can be any device in the mesh. Does not really matter
            which one.

        Returns
        -------
        Optional[datetime]
            Returns the time in datetime format
        """
        if not self.is_connected():
            error_message = "Trying to get time when not connected to Plejd mesh"
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        try:
            # Request time
            await self.send_command(
                plejd_device.ble_address,
                constants.PlejdCommand.BLE_CMD_TIME_UPDATE.value,
                "",
                constants.PlejdResponse.BLE_REQUEST_RESPONSE.value,
            )
            # Read respone
            last_data = await self.get_last_data()
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError):
            logging.error("Failed to read time from Plejd mesh, when calling get_last_data")
            raise

        # Make sure we receive the time update command
        if not last_data or not (
            int.from_bytes(last_data[3:5], "big")
            == constants.PlejdCommand.BLE_CMD_TIME_UPDATE.value
        ):
            logging.warning(
                "Failed to read time from Plejd mesh, using device: %s",
                plejd_device.name,
            )
            raise UnsupportedCommandError("Received unknown command")

        # Convert from unix timestamp
        plejd_time = datetime.fromtimestamp(struct.unpack_from("<I", last_data, 5)[0])

        return plejd_time

    async def set_plejd_time(self, plejd_device: BTDeviceInfo, time: datetime) -> bool:
        """Set time in plejd mesh.

        Parameters
        ----------
        plejd_device : PlejdDevice
            Plejd device to use to set time, can be any device in the mesh. Does not really matter
            which one.
        time : datetime
            Time to set in datetime format

        Returns
        -------
        bool
            Boolean status of the operation
        """
        timestamp = struct.pack("<I", int(time.timestamp())) + b"\x00"
        try:
            await self.send_command(
                plejd_device.ble_address,
                constants.PlejdCommand.BLE_CMD_TIME_UPDATE.value,
                timestamp.hex(),
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE.value,
            )
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            error_message = f"Failed to set time in Plejd mesh: {str(err)}"
            logging.error(error_message)
            raise

        logging.debug("Successfully set plejd time to: %s", time)
        return True

    async def _connect(self) -> bool:
        self._disconnect = False

        # Scan for Plejd devices
        try:
            scanner = bleak.BleakScanner(service_uuids=[constants.PLEJD_SERVICE])
            await scanner.start()
            await asyncio.sleep(self._settings.ble.scan_time)
            await scanner.stop()
        except (BleakError, BleakDBusError) as err:
            logging.warning(f"Could not start BLE scanner: {str(err)}")
            return False
        except Exception as err:
            logging.warning(f"Unknown error when starting BLE scanner: {str(err)}")
            return False

        logging.debug(
            f"Successfully started BLE scanner, found {len(scanner.discovered_devices)} devices"
        )

        if not scanner.discovered_devices:
            logging.warning("Could not find any plejd devices")
            return False

        # Find device with strongest signal
        curr_rssi = -255
        plejd_device = None
        for [
            device,
            advertisement,
        ] in scanner.discovered_devices_and_advertisement_data.values():
            if advertisement.rssi > curr_rssi:
                curr_rssi = advertisement.rssi
                plejd_device = device

        if not plejd_device:
            logging.warning("Could not find any plejd devices")
            return False

        logging.debug(f"Using device {plejd_device} with signal strenth {curr_rssi}")

        # Connect to plejd mesh using the selected device
        self._client = BleakClient(plejd_device)
        if not await self._client.connect():
            logging.warning("Could not connect to plejd device")
            return False

        # Authenticate to plejd mesh
        if not await self._auth_challenge_response():
            logging.warning("Could not authenticate plejd mesh")
            return False

        return True

    async def _auth_challenge_response(self) -> bool:
        # Initiate challenge
        encoded_data = b"\x00"
        try:
            await self._write_request(constants.PlejdCharacteristic.AUTH_UUID.value, encoded_data)
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            logging.warning(f"Failed to initiate auth challenge: {str(err)}")
            return False

        # Read challenge
        try:
            challenge = await self._read_request(constants.PlejdCharacteristic.AUTH_UUID.value)

            key_int = int.from_bytes(self._crypto_key, "big")
            challenge_int = int.from_bytes(challenge, "big")

            intermediate = hashlib.sha256((key_int ^ challenge_int).to_bytes(16, "big")).digest()
            part1 = int.from_bytes(intermediate[:16], "big")
            part2 = int.from_bytes(intermediate[16:], "big")
            response = (part1 ^ part2).to_bytes(16, "big")
            await self._write_request(constants.PlejdCharacteristic.AUTH_UUID.value, response)
        except (PlejdBluetoothError, PlejdNotConnectedError, PlejdTimeoutError) as err:
            logging.warning(f"Failed to perform challenge response: {str(err)}")
            return False

        return True

    async def _write_request(self, characteristic_uuid, data) -> None:
        if not self.is_connected():
            error_message = (
                f"Trying to write request to characteristic {characteristic_uuid} "
                " when not connected to Plejd mesh"
            )
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        try:
            constants.PlejdCharacteristic(characteristic_uuid)
        except ValueError as err:
            error_message = (
                f"Trying to write request to characteristic {characteristic_uuid} "
                "that is not a valid PlejdCharacteristic"
            )
            logging.error(error_message)
            raise UnsupportedCharacteristicError(error_message) from err

        try:
            await self._client.write_gatt_char(characteristic_uuid, data)
        except (BleakError, BleakDBusError) as err:
            error_message = f"Failed to write to characteristic {characteristic_uuid}: {str(err)}"
            logging.error(error_message)
            raise PlejdBluetoothError(error_message) from err
        except asyncio.TimeoutError as err:
            error_message = (
                "Timeout error when writing to characteristic " f"{characteristic_uuid}: {str(err)}"
            )
            logging.error(error_message)
            raise PlejdTimeoutError(error_message) from err

    async def _read_request(self, characteristic_uuid) -> bytearray:
        if not self.is_connected():
            error_message = (
                f"Trying to read request from characteristic {characteristic_uuid} "
                " when not connected to Plejd mesh"
            )
            logging.error(error_message)
            raise PlejdNotConnectedError(error_message)

        try:
            constants.PlejdCharacteristic(characteristic_uuid)
            data = await self._client.read_gatt_char(characteristic_uuid)
        except ValueError as err:
            error_message = (
                f"Trying to read request from characteristic {characteristic_uuid} "
                "that is not a valid PlejdCharacteristic"
            )
            logging.error(error_message)
            raise UnsupportedCharacteristicError(error_message) from err
        except (BleakError, BleakDBusError) as err:
            error_message = f"Failed to read from characteristic {characteristic_uuid}: {str(err)}"
            logging.error(error_message)
            raise PlejdBluetoothError(error_message) from err
        except asyncio.TimeoutError as err:
            error_message = (
                "Timeout error when reading from characteristic"
                f"{characteristic_uuid}: {str(err)}"
            )
            logging.error(error_message)
            raise PlejdTimeoutError(error_message) from err

        return data

    def _encrypt_decrypt_data(self, key: bytes, addr: str, data: bytearray) -> bytes:
        buf = bytearray(addr * 2)
        buf += addr[:4]

        # The API requires the use of ECB mode for encryption. This is generally considered
        # insecure, but it's necessary for compatibility with the API. Bandit will complain about
        # this, but we can ignore it.
        cipher = (
            Cipher(algorithms.AES(key), modes.ECB(), backend=default_backend())  # nosec
            .encryptor()
            .update(buf)
        )

        output = b""
        for i, byte in enumerate(data):
            output += struct.pack("B", byte ^ cipher[i % 16])

        return output

    def _encode_address(self, addr: str) -> bytes:
        ret = bytes.fromhex(addr.replace(":", ""))
        return ret[::-1]

    def _get_cmd_payload(
        self, ble_address: int, command: int, hex_str: str, response_type: int
    ) -> bytearray:
        buffer_length = 5
        payload = bytearray(buffer_length)

        struct.pack_into(
            ">BHH",
            payload,
            0,
            np.uint8(ble_address),
            np.ushort(response_type),
            np.ushort(command),
        )

        hex_data_bytes = bytearray.fromhex(hex_str)
        payload.extend(hex_data_bytes)

        return payload
