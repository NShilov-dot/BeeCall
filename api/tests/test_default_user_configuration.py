"""A new user must be provisioned from our own stack, never a vendor cloud."""

from unittest.mock import patch

from api.services.configuration.defaults import (
    DEFAULT_SERVICE_PROVIDERS,
    build_default_user_configuration,
)
from api.services.configuration.registry import ServiceProviders


def test_keys_from_environment_populate_the_default_stack():
    env = {
        "DEEPSEEK_API_KEY": "sk-deepseek",
        "DEEPGRAM_API_KEY": "dg-key",
        "OPENAI_API_KEY": "sk-openai",
    }
    with patch.dict("os.environ", env, clear=False):
        config = build_default_user_configuration()

    assert config.llm.provider == ServiceProviders.DEEPSEEK
    assert config.llm.api_key == "sk-deepseek"
    assert config.stt.provider == ServiceProviders.DEEPGRAM
    assert config.stt.api_key == "dg-key"
    assert config.tts.provider == ServiceProviders.PIPER
    assert config.embeddings.api_key == "sk-openai"


def test_piper_survives_a_keyless_environment():
    # No keys anywhere: the user still gets a working TTS (Piper is in-process),
    # and the key-requiring services are left for them to fill in.
    env = {k: "" for k in ("DEEPSEEK_API_KEY", "DEEPGRAM_API_KEY", "OPENAI_API_KEY")}
    with patch.dict("os.environ", env, clear=False):
        config = build_default_user_configuration()

    assert config.tts.provider == ServiceProviders.PIPER
    assert config.tts.api_key is None
    assert config.llm is None
    assert config.stt is None
    assert config.embeddings is None


def test_dograh_is_not_a_selectable_provider_at_all():
    # The whole point: no code path can hand out Dograh cloud credentials, and
    # the provider can't be picked in Model Configurations either.
    assert "dograh" not in {p.value for p in ServiceProviders}
    assert "dograh" not in {p.value for p in DEFAULT_SERVICE_PROVIDERS.values()}


def test_provisioning_path_has_no_cloud_client_left():
    # The old path minted a Dograh service key over HTTP in the auth layer.
    import api.services.auth.depends as depends

    assert not hasattr(depends, "create_user_configuration_with_mps_key")
    assert not hasattr(depends, "httpx")
