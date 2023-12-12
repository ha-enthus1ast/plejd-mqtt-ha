import pytest
from plejd_mqtt_ha.bt_client import BTClient
from plejd_mqtt_ha.mdl.bt_device_info import BTLightInfo
from plejd_mqtt_ha.mdl.combined_device import (
    BTDeviceError,
    CombinedLight,
    MQTTDeviceError,
)
from plejd_mqtt_ha.mdl.settings import PlejdSettings


class TestCombinedLight:
    """Test CombinedDevice class"""

    @pytest.fixture(autouse=True)
    def setup(self, mocker):
        self.bt_client = mocker.Mock(spec=BTClient)
        self.settings = mocker.Mock(spec=PlejdSettings)
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
        self.combined_light = CombinedLight(self.bt_client, self.settings, self.device_info)

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "mqtt_error, bt_error, expected_exception",
        [
            (None, None, None),
            (ConnectionError(""), None, MQTTDeviceError),
            (None, BTDeviceError(""), BTDeviceError),
        ],
    )
    async def test_start(self, mqtt_error, bt_error, expected_exception, mocker):
        """Test start method of CombinedDevice"""

        mock_mqtt_device = mocker.patch.object(
            self.combined_light, "_create_mqtt_device", side_effect=mqtt_error
        )
        mock_bt_device = mocker.patch.object(
            self.combined_light,
            "_create_bt_device",
            side_effect=bt_error,
            new_callable=mocker.AsyncMock,
        )

        if expected_exception is not None:
            with pytest.raises(expected_exception):
                await self.combined_light.start()
        else:
            await self.combined_light.start()
            mock_mqtt_device.assert_called_once()
            mock_bt_device.assert_called_once()
