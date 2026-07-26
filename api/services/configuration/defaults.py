from __future__ import annotations

"""Utilities for building default service configurations for a new user.

The defaults follow the same provider choices exposed by `/user/configurations/defaults`.
Values for `api_key` are pulled from environment variables named *{PROVIDER}_API_KEY*.

If an environment variable is missing, that particular provider configuration is
left as ``None``.
"""


import os

from loguru import logger
from pydantic import ValidationError

from api.schemas.user_configuration import UserConfiguration
from api.services.configuration.registry import (
    DeepgramSTTConfiguration,
    DeepSeekLLMConfiguration,
    OpenAIEmbeddingsConfiguration,
    PiperTTSConfiguration,
    ServiceProviders,
)

# Mapping of service to (provider enum, configuration class)
# First-version default stack: DeepSeek (Russian-capable, OpenAI-compatible so we
# can later repoint base_url at our own GPU cluster) + Deepgram STT (ru) + Piper
# TTS. Piper is ours: it runs in-process, needs no API key, and ships Russian
# voices in the image — so a fresh agent speaks without any cloud TTS credentials.
_DEFAULTS = {
    "llm": (ServiceProviders.DEEPSEEK, DeepSeekLLMConfiguration),
    "tts": (ServiceProviders.PIPER, PiperTTSConfiguration),
    "stt": (ServiceProviders.DEEPGRAM, DeepgramSTTConfiguration),
    "embeddings": (ServiceProviders.OPENAI, OpenAIEmbeddingsConfiguration),
}

# Public mapping of service name -> default provider
DEFAULT_SERVICE_PROVIDERS = {
    field: provider for field, (provider, _) in _DEFAULTS.items()
}


def build_default_user_configuration() -> UserConfiguration:
    """Build the service stack a brand-new user starts with.

    Each service's ``api_key`` comes from ``{PROVIDER}_API_KEY`` in the
    environment. A provider whose key is missing is left unset so the user
    fills it in under Model Configurations; providers that need no key at all
    (Piper runs in-process) are always included. Nothing here talks to a
    third-party service — provisioning must not depend on anyone's cloud.
    """
    sections = {}
    for field, (provider, config_cls) in _DEFAULTS.items():
        api_key = os.getenv(f"{provider.value.upper()}_API_KEY")
        try:
            sections[field] = (
                config_cls(api_key=api_key) if api_key else config_cls()
            )
        except ValidationError:
            # Provider requires a key and none was supplied — skip it.
            logger.info(
                f"Default {field} provider {provider.value} skipped: "
                f"{provider.value.upper()}_API_KEY not set"
            )
    return UserConfiguration(**sections)


__all__ = [
    "DEFAULT_SERVICE_PROVIDERS",
    "build_default_user_configuration",
]
