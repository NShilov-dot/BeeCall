from __future__ import annotations

"""Utilities for building default service configurations for a new user.

The defaults follow the same provider choices exposed by `/user/configurations/defaults`.
Values for `api_key` are pulled from environment variables named *{PROVIDER}_API_KEY*.

If an environment variable is missing, that particular provider configuration is
left as ``None``.
"""


from api.services.configuration.registry import (
    DeepgramSTTConfiguration,
    DeepSeekLLMConfiguration,
    ElevenlabsTTSConfiguration,
    OpenAIEmbeddingsConfiguration,
    ServiceProviders,
)

# Mapping of service to (provider enum, configuration class)
# First-version default stack: DeepSeek (Russian-capable, OpenAI-compatible so we
# can later repoint base_url at our own GPU cluster) + Deepgram STT (ru) + ElevenLabs.
_DEFAULTS = {
    "llm": (ServiceProviders.DEEPSEEK, DeepSeekLLMConfiguration),
    "tts": (ServiceProviders.ELEVENLABS, ElevenlabsTTSConfiguration),
    "stt": (ServiceProviders.DEEPGRAM, DeepgramSTTConfiguration),
    "embeddings": (ServiceProviders.OPENAI, OpenAIEmbeddingsConfiguration),
}

# Public mapping of service name -> default provider
DEFAULT_SERVICE_PROVIDERS = {
    field: provider for field, (provider, _) in _DEFAULTS.items()
}

__all__ = [
    "DEFAULT_SERVICE_PROVIDERS",
]
