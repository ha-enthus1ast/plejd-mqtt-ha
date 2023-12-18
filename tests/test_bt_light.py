import pytest
from plejd_mqtt_ha.bt_client import (
    PlejdBluetoothError,
    PlejdNotConnectedError,
    PlejdTimeoutError,
)
from plejd_mqtt_ha.constants import PlejdAction, PlejdCommand, PlejdResponse
from plejd_mqtt_ha.mdl.bt_device import BTLight, BTLightInfo


class TestBTLight:
    """Test BTLight class"""

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.bt_client = mocker.Mock()
        self.device_info = BTLightInfo(
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
            brightness=True,
        )
        self.bt_light = BTLight(self.bt_client, self.device_info)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "send_command_side_effect, expected_result",
        [
            (PlejdNotConnectedError(""), False),  # Not connected
            (PlejdBluetoothError(""), False),  # Bluetooth error
            (PlejdTimeoutError(""), False),  # Timeout error
            (None, True),  # Successful case
        ],
    )
    async def test_on(self, mocker, send_command_side_effect, expected_result):
        """Test on method of BTLight"""

        self.bt_client.send_command = mocker.AsyncMock(side_effect=send_command_side_effect)

        result = await self.bt_light.on()
        assert result == expected_result
        self.bt_client.send_command.assert_called_once_with(
            self.device_info.ble_address,
            PlejdCommand.BLE_CMD_STATE_CHANGE,
            PlejdAction.BLE_DEVICE_ON,
            PlejdResponse.BLE_REQUEST_NO_RESPONSE,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "send_command_side_effect, expected_result",
        [
            (PlejdNotConnectedError(""), False),  # Not connected
            (PlejdBluetoothError(""), False),  # Bluetooth error
            (PlejdTimeoutError(""), False),  # Timeout error
            (None, True),  # Successful case
        ],
    )
    async def test_off(self, mocker, send_command_side_effect, expected_result):
        """Test off method of BTLight"""

        self.bt_client.send_command = mocker.AsyncMock(side_effect=send_command_side_effect)

        result = await self.bt_light.off()
        assert result == expected_result
        self.bt_client.send_command.assert_called_once_with(
            self.device_info.ble_address,
            PlejdCommand.BLE_CMD_STATE_CHANGE,
            PlejdAction.BLE_DEVICE_OFF,
            PlejdResponse.BLE_REQUEST_NO_RESPONSE,
        )

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "send_command_side_effect, expected_result",
        [
            (PlejdNotConnectedError(""), False),  # Not connected
            (PlejdBluetoothError(""), False),  # Bluetooth error
            (PlejdTimeoutError(""), False),  # Timeout error
            (None, True),  # Successful case
        ],
    )
    async def test_brightness(self, mocker, send_command_side_effect, expected_result):
        """Test brightness method of BTLight"""
        brightness = 128
        s_brightness = brightness << 8 | brightness
        data = PlejdAction.BLE_DEVICE_DIM + f"{s_brightness:04X}"
        self.bt_client.send_command = mocker.AsyncMock(side_effect=send_command_side_effect)

        result = await self.bt_light.brightness(brightness)
        assert result == expected_result
        self.bt_client.send_command.assert_called_once_with(
            self.device_info.ble_address,
            PlejdCommand.BLE_CMD_DIM2_CHANGE,
            data,
            PlejdResponse.BLE_REQUEST_NO_RESPONSE,
        )
