"""BeeCall in-house LLM service.

The BeeCall LLM is exposed via an OpenAI-compatible /v1/chat/completions
endpoint, so the wrapper here is a thin subclass of OpenAILLMService that
only adds: configurable base_url, optional bearer auth, and per-call
correlation metadata for tracing.
"""

from pipecat.services.beecall.llm import BeeCallLLMService

__all__ = ["BeeCallLLMService"]
