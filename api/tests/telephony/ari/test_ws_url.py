"""Unit tests for ARI WebSocket URL construction.

The api_key credentials travel in the query string and Asterisk URI-decodes
query params, so special characters in the app name/password must be
percent-encoded — otherwise they corrupt the query string (``&``, ``#``),
the api_key split (``:``) or get mangled by decoding (``%``, ``+``).
"""

from api.services.telephony.ari_manager import ARIConnection
from api.services.telephony.providers.ari.provider import ARIProvider

TRICKY_PASSWORD = "p@ss&word:with%tricky+chars #1"
ENCODED_PASSWORD = "p%40ss%26word%3Awith%25tricky%2Bchars%20%231"


def _conn(password=TRICKY_PASSWORD, endpoint="http://asterisk:8088"):
    return ARIConnection(
        organization_id=1,
        telephony_configuration_id=10,
        ari_endpoint=endpoint,
        app_name="dograh",
        app_password=password,
        ws_client_name="dograh",
    )


def _provider(password=TRICKY_PASSWORD, endpoint="http://asterisk:8088"):
    return ARIProvider(
        {
            "ari_endpoint": endpoint,
            "app_name": "dograh",
            "app_password": password,
        }
    )


class TestARIConnectionWsUrl:
    def test_plain_credentials_pass_through_unchanged(self):
        url = _conn(password="dograh_dev_password").ws_url
        assert url == (
            "ws://asterisk:8088/ari/events"
            "?api_key=dograh:dograh_dev_password"
            "&app=dograh"
            "&subscribeAll=true"
        )

    def test_special_characters_are_percent_encoded(self):
        url = _conn().ws_url
        assert f"api_key=dograh:{ENCODED_PASSWORD}" in url
        assert TRICKY_PASSWORD not in url

    def test_https_endpoint_maps_to_wss(self):
        url = _conn(endpoint="https://asterisk.example.com:8089").ws_url
        assert url.startswith("wss://asterisk.example.com:8089/ari/events")


class TestARIProviderWsUrl:
    def test_matches_connection_encoding(self):
        # Both URL builders must produce the same shape — the manager and the
        # provider talk to the same Asterisk.
        assert _provider().get_ws_url() == _conn().ws_url
