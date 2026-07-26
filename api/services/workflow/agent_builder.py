"""Build a starter workflow from a natural-language description.

Replaces the hosted Dograh MPS call (`services.dograh.com`), which answers
401 "No active service key found" for self-hosted deployments — that is what
broke "Create Agent → Use Agent Builder". Generation now runs on the
organization's own configured LLM (any OpenAI-compatible chat endpoint,
e.g. DeepSeek).

The generated graph is a single `startCall` node on purpose: that is the
starting point `mcp_server/instructions.py` recommends, and it publishes
as-is (startCall has no outgoing-edge constraint). Users grow the graph in
the editor, which is what the post-create dialog already tells them to do.
"""

from __future__ import annotations

from loguru import logger
from openai import AsyncOpenAI

from api.db import db_client
from api.services.configuration.registry import ServiceProviders
from api.services.gen_ai.json_parser import parse_llm_json
from api.services.workflow.dto import ReactFlowDTO

_TIMEOUT_SECONDS = 60.0

# Providers whose chat API isn't OpenAI-compatible at all — an AsyncOpenAI call
# can't reach them, so say so instead of leaking a stranger's 401.
_NON_OPENAI_PROVIDERS = {
    ServiceProviders.GOOGLE.value,
    ServiceProviders.GOOGLE_VERTEX.value,
    ServiceProviders.AWS_BEDROCK.value,
}

_SYSTEM_PROMPT = """You write prompts for voice AI agents that talk to humans over the phone.

Return ONLY a JSON object with the keys "name", "greeting" and "prompt":
- "name": short agent name, max 40 characters.
- "greeting": the first sentence the agent speaks when the call starts.
- "prompt": the agent's system prompt, markdown with "# Goal", "## Rules" and "### Flow" sections.

Write "name", "greeting" and "prompt" in the same language as the use case and \
activity description given by the user.

The prompt must instruct the agent to:
- keep every answer to 1-2 short spoken sentences;
- expect transcription errors and accept variants of yes/no;
- repeat its last line when asked to repeat, rephrasing instead of looping;
- never invent facts it was not given;
- end the call politely once the goal is reached.

Call direction is {call_type}: INBOUND means the human calls the agent, \
OUTBOUND means the agent calls the human."""


class LLMNotConfiguredError(Exception):
    """The organization has no LLM configured to generate the workflow with."""


class AgentGenerationError(Exception):
    """The LLM call failed or returned something unusable."""


def _definition(name: str, prompt: str, greeting: str | None) -> dict:
    """Single-node ReactFlow definition, matching the Blank Canvas shape."""
    return {
        "nodes": [
            {
                "id": "1",
                "type": "startCall",
                "position": {"x": 175, "y": 60},
                "data": {
                    "name": name,
                    "prompt": prompt,
                    "greeting": greeting,
                    "greeting_type": "text" if greeting else None,
                    "is_start": True,
                    "allow_interrupt": True,
                    "add_global_prompt": False,
                },
            }
        ],
        "edges": [],
        "viewport": {"x": 808, "y": 269, "zoom": 0.75},
    }


async def build_workflow_from_description(
    user_id: int,
    call_type: str,
    use_case: str,
    activity_description: str,
) -> dict:
    """Generate `{"name", "workflow_definition"}` from a use-case description.

    Raises:
        LLMNotConfiguredError: no LLM configured for this user's organization.
        AgentGenerationError: the LLM call failed or returned no prompt.
    """
    user_config = await db_client.get_user_configurations(user_id)
    llm = user_config.llm
    if llm is None:
        raise LLMNotConfiguredError(
            "No LLM configured. Set an LLM provider and API key in "
            "Model Configurations before using the Agent Builder."
        )

    provider = getattr(llm.provider, "value", llm.provider)
    if provider in _NON_OPENAI_PROVIDERS:
        raise LLMNotConfiguredError(
            f"The Agent Builder needs an OpenAI-compatible LLM, and {provider} "
            "isn't one. Switch Model Configurations > LLM to DeepSeek, OpenAI or "
            "another OpenAI-compatible provider to generate agents."
        )

    try:
        # Gateways that authenticate by network policy accept any bearer token,
        # but the OpenAI client refuses to start without one.
        async with AsyncOpenAI(
            api_key=llm.api_key or "unused",
            # None means the client's own default endpoint (OpenAI).
            base_url=getattr(llm, "base_url", None),
            timeout=_TIMEOUT_SECONDS,
        ) as client:
            response = await client.chat.completions.create(
                model=llm.model,
                temperature=0.4,
                messages=[
                    {
                        "role": "system",
                        "content": _SYSTEM_PROMPT.format(call_type=call_type),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Use case: {use_case}\n"
                            f"Activity description: {activity_description}"
                        ),
                    },
                ],
            )
    except Exception as e:
        logger.error(f"Agent builder LLM call failed ({provider}/{llm.model}): {e}")
        raise AgentGenerationError(
            f"Could not reach the configured LLM ({provider}): {e}"
        )

    generated = parse_llm_json(response.choices[0].message.content or "")
    prompt = (generated.get("prompt") or "").strip()
    if not prompt:
        logger.error(f"Agent builder got no usable prompt from LLM: {generated}")
        raise AgentGenerationError(
            "The LLM did not return a usable agent prompt. Please try again."
        )

    name = (generated.get("name") or "").strip() or f"{use_case} - {call_type}"
    greeting = (generated.get("greeting") or "").strip() or None
    definition = _definition(name[:100], prompt, greeting)

    # Fail here rather than persisting a definition the editor can't load.
    ReactFlowDTO.model_validate(definition)

    return {"name": name[:100], "workflow_definition": definition}
