"""Rewrite users' model configurations to the current default stack.

One-off migration for accounts provisioned before we left Dograh's cloud: they
still hold `dograh` providers with expired service keys. Rewrites each user's
config with `build_default_user_configuration()` — DeepSeek LLM + Deepgram STT
+ Piper TTS, keys read from {PROVIDER}_API_KEY.

Piped into the api container, which already has the keys from compose (the
image ships only start_services_docker.sh, so stdin beats a Dockerfile change):

    docker exec -i -w /app dograh-api-1 python - < scripts/reset_user_configurations.py
    docker exec -i -w /app dograh-api-1 python - 5 < scripts/reset_user_configurations.py

…or on the host with the venv and api/.env sourced. Pass user ids to limit the
scope; with no arguments every user is rewritten.

This overwrites configurations, so it refuses to run when no LLM key is set —
otherwise it would silently strip working credentials and leave TTS only.
"""

import asyncio
import sys

from sqlalchemy import select

from api.db import db_client
from api.db.models import UserModel
from api.services.configuration.defaults import build_default_user_configuration


async def _all_user_ids() -> list[int]:
    """Owned by this script — no need for a shared client method for a one-off."""
    async with db_client.async_session() as session:
        result = await session.execute(select(UserModel.id).order_by(UserModel.id))
        return list(result.scalars().all())


async def main(user_ids: list[int]) -> int:
    config = build_default_user_configuration()
    if config.llm is None:
        print(
            "Refusing to run: no LLM key in the environment "
            "(set DEEPSEEK_API_KEY), so this would wipe existing credentials "
            "and leave Piper TTS alone.",
            file=sys.stderr,
        )
        return 1

    stack = ", ".join(
        f"{field}={getattr(config, field).provider.value}"
        for field in ("llm", "stt", "tts", "embeddings")
        if getattr(config, field) is not None
    )
    print(f"Target stack: {stack}")

    if not user_ids:
        user_ids = await _all_user_ids()

    for user_id in user_ids:
        user = await db_client.get_user_by_id(user_id)
        if not user:
            print(f"  user {user_id}: not found, skipped")
            continue
        before = await db_client.get_user_configurations(user_id)
        was = before.llm.provider.value if before.llm else "<unset>"
        await db_client.update_user_configuration(user_id, config)
        print(f"  user {user_id}: llm {was} -> {config.llm.provider.value}")

    print(f"Done: {len(user_ids)} user(s) processed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main([int(a) for a in sys.argv[1:]])))
