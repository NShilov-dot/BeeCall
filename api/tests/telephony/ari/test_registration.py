"""Unit tests for the ARI provider's registry contract.

These tests assert the wiring that the rest of the telephony layer relies on:
the spec is registered under the right name, sample rate matches what
chan_websocket produces (8 kHz mu-law), and the config_loader normalizes
stored credentials into the dict the provider constructor expects.

No DB / Redis / Asterisk needed — this is import-time state plus pure
functions.
"""

import pytest
from pydantic import ValidationError

from api.services.telephony import registry
from api.services.telephony.providers.ari import SPEC, _config_loader
from api.services.telephony.providers.ari.config import (
    ARIConfigurationRequest,
    ARIConfigurationResponse,
)
from api.services.telephony.providers.ari.provider import ARIProvider


class TestARIRegistration:
    def test_spec_registered_under_name_ari(self):
        assert registry.get("ari") is SPEC

    def test_spec_name_and_provider_class(self):
        assert SPEC.name == "ari"
        assert SPEC.provider_cls is ARIProvider

    def test_transport_sample_rate_matches_chan_websocket(self):
        # chan_websocket emits raw G.711 mu-law at 8 kHz. If this drifts the
        # AsteriskFrameSerializer will resample silently — better to fail loud.
        assert SPEC.transport_sample_rate == 8000

    def test_config_classes_carry_the_ari_discriminator(self):
        assert SPEC.config_request_cls is ARIConfigurationRequest
        assert SPEC.config_response_cls is ARIConfigurationResponse

    def test_ui_metadata_marks_password_sensitive(self):
        # Sensitivity is the single source of truth for masking on read.
        # Forgetting `sensitive=True` would leak the ARI password.
        password_field = next(
            f for f in SPEC.ui_metadata.fields if f.name == "app_password"
        )
        assert password_field.sensitive is True

    def test_ui_metadata_exposes_required_fields(self):
        names = {f.name for f in SPEC.ui_metadata.fields}
        assert {
            "ari_endpoint",
            "app_name",
            "app_password",
            "ws_client_name",
            "trunk_name",
        } <= names


class TestConfigLoader:
    def test_loader_picks_only_known_keys(self):
        raw = {
            "ari_endpoint": "http://asterisk:8088",
            "app_name": "dograh",
            "app_password": "secret",
            "ws_client_name": "dograh",
            "trunk_name": "beeline",
            "from_numbers": ["6001"],
            "rogue_field": "should be dropped",
        }
        loaded = _config_loader(raw)
        assert loaded == {
            "provider": "ari",
            "ari_endpoint": "http://asterisk:8088",
            "app_name": "dograh",
            "app_password": "secret",
            "trunk_name": "beeline",
            "from_numbers": ["6001"],
        }
        assert "rogue_field" not in loaded

    def test_loader_defaults_from_numbers_to_empty_list(self):
        loaded = _config_loader({"ari_endpoint": "x", "app_name": "y", "app_password": "z"})
        assert loaded["from_numbers"] == []


class TestARIConfigurationRequest:
    def test_minimal_valid_request(self):
        req = ARIConfigurationRequest(
            ari_endpoint="http://asterisk:8088",
            app_name="dograh",
            app_password="dograh_dev_password",
        )
        assert req.provider == "ari"
        assert req.from_numbers == []
        assert req.ws_client_name == ""
        assert req.trunk_name == ""

    def test_provider_discriminator_locked_to_ari(self):
        # The discriminated Union in schemas/telephony_config.py dispatches on
        # `provider`; if it accepts anything else the wrong save handler runs.
        with pytest.raises(ValidationError):
            ARIConfigurationRequest(
                provider="twilio",  # type: ignore[arg-type]
                ari_endpoint="http://asterisk:8088",
                app_name="dograh",
                app_password="x",
            )

    def test_required_credentials_missing(self):
        with pytest.raises(ValidationError):
            ARIConfigurationRequest(  # type: ignore[call-arg]
                ari_endpoint="http://asterisk:8088",
                app_name="dograh",
                # no app_password
            )
