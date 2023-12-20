import pytest
import requests
from plejd_mqtt_ha.mdl.settings import API, PlejdSettings
from plejd_mqtt_ha.plejd_api import (
    IncorrectCredentialsError,
    PlejdAPI,
    PlejdAPIError,
    UnknownResponseError,
)


class TestPlejdAPI:
    """Test PlejdAPI class"""

    @pytest.fixture(autouse=True)
    def setup(self):
        self.settings = PlejdSettings(
            api=API(user="test_user", password="test_password", cache_policy="NO_CACHE")
        )

    @pytest.mark.parametrize(
        "status_code,return_value,expected",
        [
            (200, {"sessionToken": "test_token"}, "test_token"),
            (401, {}, IncorrectCredentialsError),
            (200, {}, UnknownResponseError),
            (500, {}, PlejdAPIError),
        ],
    )
    def test_login(self, mocker, status_code, return_value, expected):
        """Test login method of PlejdAPI"""
        mock_response = mocker.Mock()
        mock_response.status_code = status_code
        mock_response.json.return_value = return_value
        if status_code >= 400:
            mock_response.raise_for_status.side_effect = requests.HTTPError()
        mocker.patch("requests.post", return_value=mock_response)

        api = PlejdAPI(self.settings)
        if expected == IncorrectCredentialsError:
            with pytest.raises(expected):
                api.login()
        elif expected == UnknownResponseError:
            with pytest.raises(expected):
                api.login()
        elif expected == PlejdAPIError:
            with pytest.raises(PlejdAPIError):
                api.login()
        else:
            api.login()
            assert api._session_token == expected

    # TODO add positive test for get_site

    @pytest.mark.parametrize(
        "exception",
        [requests.RequestException, ValueError, UnknownResponseError("")],
    )
    def test_get_site_exceptions(self, mocker, exception):
        """Test get_site method of PlejdAPI when an exception is raised"""
        api = PlejdAPI(self.settings)
        api._session_token = "test_token"

        mocker.patch("requests.post", side_effect=exception)
        with pytest.raises(PlejdAPIError):
            api.get_site("cache_file")
