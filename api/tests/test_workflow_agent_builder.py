"""Agent Builder generates a workflow the editor can load and publish."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import pytest

from api.schemas.user_configuration import UserConfiguration
from api.services.configuration.registry import DeepSeekLLMConfiguration
from api.services.workflow.agent_builder import (
    AgentGenerationError,
    LLMNotConfiguredError,
    build_workflow_from_description,
)
from api.services.workflow.dto import ReactFlowDTO
from api.services.workflow.workflow_graph import WorkflowGraph


def _llm_reply(content: str):
    """Shape of openai's chat.completions.create response."""
    return SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
    )


def _patch_llm(content: str):
    """Patch the OpenAI client used by the builder, returning `content`."""
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(return_value=_llm_reply(content))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)
    return patch(
        "api.services.workflow.agent_builder.AsyncOpenAI", return_value=client
    )


def _patch_config(config: UserConfiguration):
    return patch(
        "api.services.workflow.agent_builder.db_client.get_user_configurations",
        AsyncMock(return_value=config),
    )


def _deepseek_config() -> UserConfiguration:
    return UserConfiguration(
        llm=DeepSeekLLMConfiguration(api_key="sk-test", model="deepseek-chat")
    )


async def _build(llm_output: str, config: UserConfiguration | None = None):
    with _patch_config(config or _deepseek_config()), _patch_llm(llm_output):
        return await build_workflow_from_description(
            user_id=1,
            call_type="INBOUND",
            use_case="Поддержка абонентов",
            activity_description="Отвечать на вопросы о тарифах",
        )


@pytest.mark.asyncio
async def test_generated_workflow_is_valid_and_publishable():
    result = await _build(
        '```json\n{"name": "Агент поддержки", "greeting": "Здравствуйте!", '
        '"prompt": "# Goal\\nОтвечать на вопросы о тарифах."}\n```'
    )

    assert result["name"] == "Агент поддержки"

    # Same gates the editor and /publish apply.
    dto = ReactFlowDTO.model_validate(result["workflow_definition"])
    WorkflowGraph(dto)

    node = result["workflow_definition"]["nodes"][0]
    assert node["type"] == "startCall"
    assert node["data"]["is_start"] is True
    assert "тарифах" in node["data"]["prompt"]
    assert node["data"]["greeting"] == "Здравствуйте!"
    assert node["data"]["greeting_type"] == "text"


@pytest.mark.asyncio
async def test_falls_back_to_use_case_name_and_no_greeting():
    result = await _build('{"prompt": "# Goal\\nHelp the caller."}')

    assert result["name"] == "Поддержка абонентов - INBOUND"
    node = result["workflow_definition"]["nodes"][0]
    assert node["data"]["greeting"] is None
    assert node["data"]["greeting_type"] is None
    WorkflowGraph(ReactFlowDTO.model_validate(result["workflow_definition"]))


@pytest.mark.asyncio
async def test_deepseek_keeps_its_configured_base_url():
    with (
        _patch_config(_deepseek_config()),
        _patch_llm('{"prompt": "# Goal\\nHelp."}') as mock_client_cls,
    ):
        await build_workflow_from_description(
            user_id=1,
            call_type="INBOUND",
            use_case="Поддержка",
            activity_description="Отвечать на вопросы",
        )

    assert mock_client_cls.call_args.kwargs["base_url"] == "https://api.deepseek.com/v1"


@pytest.mark.asyncio
async def test_non_openai_provider_says_what_to_switch_to():
    from api.services.configuration.registry import GoogleLLMService

    config = UserConfiguration(
        llm=GoogleLLMService(api_key="key", model="gemini-2.0-flash")
    )
    with pytest.raises(LLMNotConfiguredError, match="OpenAI-compatible"):
        await _build("unused", config=config)


@pytest.mark.asyncio
async def test_missing_llm_config_raises_actionable_error():
    with pytest.raises(LLMNotConfiguredError, match="Model Configurations"):
        await _build("unused", config=UserConfiguration())


@pytest.mark.asyncio
async def test_empty_api_key_fails_before_calling_deepseek():
    """No key for a public provider → clean error, never sends "unused"."""
    config = UserConfiguration(
        llm=DeepSeekLLMConfiguration(api_key=None, model="deepseek-chat")
    )
    with _patch_config(config), _patch_llm("unused") as mock_client_cls:
        with pytest.raises(LLMNotConfiguredError, match="Model Configurations"):
            await build_workflow_from_description(
                user_id=1,
                call_type="INBOUND",
                use_case="Поддержка",
                activity_description="Отвечать на вопросы",
            )
    mock_client_cls.assert_not_called()


@pytest.mark.asyncio
async def test_unusable_llm_output_raises():
    with pytest.raises(AgentGenerationError):
        await _build("Sorry, I cannot help with that.")


@pytest.mark.asyncio
async def test_llm_transport_failure_raises_generation_error():
    client = AsyncMock()
    client.chat.completions.create = AsyncMock(side_effect=RuntimeError("timeout"))
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=False)

    with (
        _patch_config(_deepseek_config()),
        patch(
            "api.services.workflow.agent_builder.AsyncOpenAI", return_value=client
        ),
        pytest.raises(AgentGenerationError, match="deepseek"),
    ):
        await build_workflow_from_description(
            user_id=1,
            call_type="OUTBOUND",
            use_case="Обзвон",
            activity_description="Напомнить об оплате",
        )
