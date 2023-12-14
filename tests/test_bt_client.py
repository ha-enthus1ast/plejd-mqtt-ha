import datetime
import struct

import pytest
from plejd_mqtt_ha import constants
from plejd_mqtt_ha.bt_client import (
    BTClient,
    PlejdBluetoothError,
    PlejdNotConnectedError,
    UnsupportedCommandError,
)
from plejd_mqtt_ha.mdl.bt_device_info import BTDeviceInfo
from plejd_mqtt_ha.mdl.settings import API, PlejdSettings


class TestBTClient:
    """Test BTClient class"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.settings = PlejdSettings(api=API(user="test_user", password="test_password"))
        self.bt_client = BTClient("deadbeef", self.settings)
        self.bt_device = BTDeviceInfo(
            category="category",
            model="model",
            device_id=1,
            unique_id="unique_id",
            hardware_id="hardware_id",
            index=1,
            name="device",
            ble_address=1,
            plejd_id=1,
            device_type="type",
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_connected,_connect,expected",
        [
            (True, True, True),  # Already connected
            (False, True, True),  # Connect success
            (False, False, False),  # Connect failed
        ],
    )
    async def test_connect(self, mocker, is_connected, _connect, expected):
        """Test connect method of BTClient"""
        self.bt_client.is_connected = mocker.MagicMock(return_value=is_connected)
        self.bt_client._connect = mocker.AsyncMock(return_value=_connect)
        self.bt_client._stay_connected_loop = mocker.MagicMock()

        result = await self.bt_client.connect(stay_connected=False)

        assert result == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_connected,_disconnect,expected",
        [
            (True, True, True),  # Already connected, disconnect should be successful
            (False, True, True),  # Not connected, disconnect should still return True
            (True, False, False),  # Connected, disconnect should return False
            (False, False, True),  # Not connected, no disconnect should be attempted
        ],
    )
    async def test_disconnect(self, mocker, is_connected, _disconnect, expected):
        """Test disconnect method of BTClient"""
        self.bt_client.is_connected = mocker.MagicMock(return_value=is_connected)
        self.bt_client._client = mocker.MagicMock()
        self.bt_client._client.disconnect = mocker.AsyncMock(return_value=_disconnect)

        result = await self.bt_client.disconnect()

        assert result == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_connected,command,write_request_success,expected_exception",
        [
            (False, 0, True, PlejdNotConnectedError),  # Not connected
            (True, -1, True, UnsupportedCommandError),  # Invalid command
            (
                True,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                False,
                PlejdBluetoothError,
            ),  # Write request failed
            (
                True,
                constants.PlejdCommand.BLE_CMD_STATE_CHANGE,
                True,
                None,
            ),  # Successful case
        ],
    )
    async def test_send_command(
        self, mocker, is_connected, command, write_request_success, expected_exception
    ):
        """Test send_command method of BTClient"""
        self.bt_client.is_connected = mocker.MagicMock(return_value=is_connected)
        self.bt_client._get_cmd_payload = mocker.MagicMock(return_value="payload")
        self.bt_client._client = mocker.MagicMock(address="address")
        self.bt_client._encode_address = mocker.MagicMock(return_value="encoded_address")
        self.bt_client._encrypt_decrypt_data = mocker.MagicMock(return_value="encrypted_data")
        self.bt_client._write_request = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("Write request failed")
            if not write_request_success
            else None
        )

        if expected_exception:
            with pytest.raises(expected_exception):
                await self.bt_client.send_command(1, command, "data", 1)
        else:
            await self.bt_client.send_command(1, command, "data", 1)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "write_request_success, read_request_success, pong_data, expected",
        [
            (False, True, b"\x01", False),  # Write request failed
            (True, False, b"\x01", False),  # Read request failed
            (True, True, b"", False),  # Pong data is empty
            (True, True, b"\x02", False),  # Pong data is not the expected value
            (True, True, b"\x01", True),  # Successful case
        ],
    )
    async def test_ping(
        self, mocker, write_request_success, read_request_success, pong_data, expected
    ):
        """Test ping method of BTClient"""
        ping_data = b"\x00"
        mocker.patch("plejd_mqtt_ha.bt_client.randbytes", return_value=ping_data)
        self.bt_client._write_request = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("Write request failed")
            if not write_request_success
            else None
        )

        self.bt_client._read_request = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("Read request failed")
            if not read_request_success
            else None,
            return_value=pong_data,
        )
        result = await self.bt_client.ping()

        assert result == expected

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_connected, read_request_success, encrypted_data, expected_exception",
        [
            (False, True, b"\x01", PlejdNotConnectedError),  # Not connected
            (True, False, b"\x01", PlejdBluetoothError),  # _read_request failed
            (True, True, b"\x01", None),  # Successful case
        ],
    )
    async def test_get_last_data(
        self,
        mocker,
        is_connected,
        read_request_success,
        encrypted_data,
        expected_exception,
    ):
        """Test get_last_data method of BTClient"""
        self.bt_client.is_connected = mocker.MagicMock(return_value=is_connected)
        self.bt_client._client = mocker.MagicMock(address="address")
        self.bt_client._encode_address = mocker.MagicMock(return_value="encoded_address")
        self.bt_client._encrypt_decrypt_data = mocker.MagicMock(return_value="decrypted_data")
        self.bt_client._read_request = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("Read request failed")
            if not read_request_success
            else None,
            return_value=encrypted_data,
        )

        if expected_exception:
            with pytest.raises(expected_exception):
                await self.bt_client.get_last_data()
        else:
            result = await self.bt_client.get_last_data()
            assert result == "decrypted_data"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "is_connected,"
        "send_command_success,"
        "get_last_data_success,"
        "last_data,"
        "expected_exception,"
        "expected_result",
        [
            (
                False,
                True,
                True,
                b"\x01\x02\x03\x04\x05\x06\x07\x08",
                PlejdNotConnectedError,
                None,
            ),  # Not connected
            (
                True,
                False,
                True,
                b"\x01\x02\x03\x04\x05\x06\x07\x08",
                PlejdBluetoothError,
                None,
            ),  # send_command failed
            (
                True,
                True,
                False,
                b"\x01\x02\x03\x04\x05\x06\x07\x08",
                PlejdBluetoothError,
                None,
            ),  # get_last_data failed
            (
                True,
                True,
                True,
                b"\x01\x02\x03\x04\x05\x06\x07\x08",
                UnsupportedCommandError,
                None,
            ),  # Invalid last_data
            (
                True,
                True,
                True,
                b"\x01\x02\x00\x00\x1b\x00\x00\x00\x00\x00\x00\x00",
                None,
                datetime.datetime.fromtimestamp(0),
            ),  # Successful case
        ],
    )
    async def test_get_plejd_time(
        self,
        mocker,
        is_connected,
        send_command_success,
        get_last_data_success,
        last_data,
        expected_exception,
        expected_result,
    ):
        """Test get_plejd_time method of BTClient"""

        self.bt_client.is_connected = mocker.MagicMock(return_value=is_connected)
        self.bt_client.send_command = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("send_command failed")
            if not send_command_success
            else None
        )
        self.bt_client.get_last_data = mocker.AsyncMock(
            side_effect=PlejdBluetoothError("get_last_data failed")
            if not get_last_data_success
            else None,
            return_value=last_data,
        )

        if expected_exception:
            with pytest.raises(expected_exception):
                await self.bt_client.get_plejd_time(self.bt_device.ble_address)
        else:
            result = await self.bt_client.get_plejd_time(self.bt_device.ble_address)
            assert result == expected_result

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "send_command_success, expected_exception, expected_result",
        [
            (False, PlejdNotConnectedError(""), False),  # Not connected
            (False, PlejdBluetoothError(""), False),  # send_command failed
            (False, None, None),  # Successful case
        ],
    )
    async def test_set_plejd_time(
        self, mocker, send_command_success, expected_exception, expected_result
    ):
        """Test set_plejd_time method of BTClient"""

        time = datetime.datetime.now()
        timestamp = struct.pack("<I", int(time.timestamp())) + b"\x00"
        self.bt_client.send_command = mocker.AsyncMock(
            side_effect=expected_exception if not send_command_success else None
        )

        if expected_exception:
            with pytest.raises(type(expected_exception)):
                await self.bt_client.set_plejd_time(self.bt_device.ble_address, time)
        else:
            result = await self.bt_client.set_plejd_time(self.bt_device.ble_address, time)
            assert result == expected_result
            self.bt_client.send_command.assert_called_once_with(
                self.bt_device.ble_address,
                constants.PlejdCommand.BLE_CMD_TIME_UPDATE.value,
                timestamp.hex(),
                constants.PlejdResponse.BLE_REQUEST_NO_RESPONSE.value,
            )
