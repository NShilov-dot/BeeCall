#
# Copyright (c) 2024–2025, Daily
#
# SPDX-License-Identifier: BSD 2-Clause License
#

"""BeeCall LLM service — thin wrapper over OpenAI-compatible endpoint."""

from loguru import logger

from pipecat.frames.frames import Frame, StartFrame
from pipecat.processors.frame_processor import FrameDirection
from pipecat.services.openai.base_llm import OpenAILLMInvocationParams, OpenAILLMSettings
from pipecat.services.openai.llm import OpenAILLMService


class BeeCallLLMService(OpenAILLMService):
    """In-house LLM service using BeeCall's OpenAI-compatible API.

    Inherits the full OpenAI chat-completions surface from ``OpenAILLMService``:
    streaming, function/tool calling, vision/audio content blocks, and the
    standard error frames. The only adapter-specific behavior is injecting
    ``workflow_run_id`` as ``metadata.correlation_id`` so server-side traces
    can be joined with our pipeline traces.
    """

    def __init__(
        self,
        *,
        api_key: str | None,
        base_url: str,
        settings: OpenAILLMSettings | None = None,
        **kwargs,
    ):
        """Initialize the BeeCall LLM service.

        Args:
            api_key: Bearer token. May be ``None`` if the gateway authenticates
                via network policy (mTLS / VPC). The AsyncOpenAI client requires
                *some* string, so we substitute a placeholder downstream.
            base_url: Root of the OpenAI-compatible endpoint, e.g.
                ``https://llm.beecall.internal/v1``. Do **not** append
                ``/chat/completions`` — the SDK does that.
            settings: ``OpenAILLMSettings`` carrying model name, temperature,
                etc. If omitted, defaults to ``model="default"``.
            **kwargs: Forwarded to ``OpenAILLMService``.
        """
        default_settings = OpenAILLMSettings(model="default")
        if settings is not None:
            default_settings.apply_update(settings)

        # AsyncOpenAI rejects an empty/None api_key string. When the gateway
        # uses network-level auth we still need a non-empty placeholder.
        effective_api_key = api_key or "none"

        self._base_url = base_url
        super().__init__(
            api_key=effective_api_key,
            base_url=base_url,
            settings=default_settings,
            **kwargs,
        )
        self._start_metadata: dict | None = None

    async def process_frame(self, frame: Frame, direction: FrameDirection) -> None:
        """Capture StartFrame metadata so we can attach it to completion calls."""
        if isinstance(frame, StartFrame):
            self._start_metadata = frame.metadata

        await super().process_frame(frame, direction)

    def build_chat_completion_params(
        self, params_from_context: OpenAILLMInvocationParams
    ) -> dict:
        """Attach correlation_id from the originating workflow run.

        The OpenAI request schema reserves ``metadata`` for caller-supplied
        key/value pairs. We forward ``workflow_run_id`` so the in-house gateway
        can stitch its logs to our pipeline traces without parsing prompts.
        """
        params = super().build_chat_completion_params(params_from_context)

        if self._start_metadata and "workflow_run_id" in self._start_metadata:
            params.setdefault("metadata", {})
            params["metadata"]["correlation_id"] = str(
                self._start_metadata["workflow_run_id"]
            )

        logger.debug(
            f"BeeCall LLM request: base_url={self._base_url} "
            f"model={params.get('model')} "
            f"correlation_id={params.get('metadata', {}).get('correlation_id')}"
        )
        return params
