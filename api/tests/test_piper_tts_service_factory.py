"""Piper is the in-process TTS default — the factory must wire it, not 400."""

from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from api.services.configuration.defaults import DEFAULT_SERVICE_PROVIDERS
from api.services.configuration.registry import (
    PiperTTSConfiguration,
    ServiceProviders,
)
from api.services.pipecat.service_factory import PIPER_VOICES_DIR, create_tts_service

pytest.importorskip("piper", reason="requires pipecat-ai[piper]")


def _user_config(**overrides):
    tts = SimpleNamespace(
        provider=ServiceProviders.PIPER.value,
        model="piper",
        voice="ru_RU-irina-medium",
        api_key=None,
        use_cuda=False,
    )
    for key, value in overrides.items():
        setattr(tts, key, value)
    return SimpleNamespace(tts=tts)


def _audio_config():
    return SimpleNamespace(
        transport_out_sample_rate=8000,
        transport_in_sample_rate=8000,
        pipeline_sample_rate=8000,
    )


def test_create_piper_tts_service_passes_voice_and_baked_voices_dir():
    with patch("pipecat.services.piper.tts.PiperTTSService") as mock_service:
        create_tts_service(_user_config(), _audio_config())

    assert mock_service.call_count == 1
    kwargs = mock_service.call_args.kwargs
    assert kwargs["settings"].voice == "ru_RU-irina-medium"
    assert kwargs["use_cuda"] is False
    # Must be a Path: pipecat hands it to piper's download_voice, which does
    # `download_dir / f"{voice}.onnx"` and blows up on a str.
    assert kwargs["download_dir"] == PIPER_VOICES_DIR
    assert PIPER_VOICES_DIR.is_absolute()


def test_create_piper_tts_service_honours_use_cuda():
    with patch("pipecat.services.piper.tts.PiperTTSService") as mock_service:
        create_tts_service(_user_config(use_cuda=True), _audio_config())

    assert mock_service.call_args.kwargs["use_cuda"] is True


def test_piper_config_has_no_dead_speed_knob():
    # pipecat's PiperTTSService forwards only voice/language, so a speed field
    # would silently do nothing.
    assert "speed" not in PiperTTSConfiguration.model_fields


def test_piper_is_the_default_tts_provider():
    # A fresh org must speak without any cloud TTS credentials.
    assert DEFAULT_SERVICE_PROVIDERS["tts"] == ServiceProviders.PIPER


def test_piper_config_passes_validity_check_without_api_key():
    # _check_api_key returns False for any provider missing from _validator_map,
    # so without the Piper early return the default TTS reads as invalid.
    from api.services.configuration.check_validity import UserConfigurationValidator

    statuses = UserConfigurationValidator()._validate_service(
        PiperTTSConfiguration(voice="ru_RU-irina-medium"), "tts"
    )
    assert statuses == []


def test_unknown_tts_provider_still_rejected():
    with pytest.raises(HTTPException) as exc:
        create_tts_service(_user_config(provider="nope"), _audio_config())
    assert exc.value.status_code == 400
