"""Unit tests for ARIConnection event routing and teardown.

StasisStart routing is args-based, not state-based: a dialplan is free to
Answer() before Stasis() (delivering the channel in state "Up"), so the only
reliable discriminator is what appArgs carry — nothing for inbound, workflow
context for our originates, ["transfer", id] for transfer destinations.

StasisEnd teardown must hang up every leg recorded in gathered_context,
including the transfer destination left bridged with the caller after a
completed transfer.

No network or Redis — ARI REST helpers and Redis-backed lookups are mocked.
"""

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from api.services.telephony import ari_manager as ari_manager_module
from api.services.telephony.ari_manager import ARIConnection


def _make_conn() -> ARIConnection:
    return ARIConnection(
        organization_id=1,
        telephony_configuration_id=10,
        ari_endpoint="http://asterisk:8088",
        app_name="dograh",
        app_password="dograh_dev_password",
        ws_client_name="dograh",
    )


def _stasis_start(channel_id="chan-1", state="Ring", args=None) -> str:
    return json.dumps(
        {
            "type": "StasisStart",
            "args": args or [],
            "channel": {
                "id": channel_id,
                "state": state,
                "caller": {"number": "6001"},
                "dialplan": {"exten": "8001"},
            },
        }
    )


async def _drain_tasks():
    """Handlers are spawned via create_task — yield so they get to run."""
    await asyncio.sleep(0)


class TestStasisStartRouting:
    @pytest.mark.parametrize("state", ["Ring", "Up"])
    async def test_bare_stasis_routes_inbound_regardless_of_state(self, state):
        # The dialplan may Answer() before Stasis(); inbound routing must not
        # depend on the channel still being in "Ring".
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=False)
        conn._handle_inbound_stasis_start = AsyncMock()
        conn._handle_stasis_start = AsyncMock()

        await conn._handle_event(_stasis_start(state=state, args=[]))
        await _drain_tasks()

        conn._handle_inbound_stasis_start.assert_awaited_once()
        conn._handle_stasis_start.assert_not_awaited()

    async def test_workflow_args_route_outbound(self):
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=False)
        conn._handle_inbound_stasis_start = AsyncMock()
        conn._handle_stasis_start = AsyncMock()

        await conn._handle_event(
            _stasis_start(state="Up", args=["workflow_run_id=5,workflow_id=2,user_id=3"])
        )
        await _drain_tasks()

        conn._handle_stasis_start.assert_awaited_once_with("chan-1", "Up", "5", "2", "3")
        conn._handle_inbound_stasis_start.assert_not_awaited()

    async def test_transfer_args_route_destination_answered(self):
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=False)
        conn._handle_destination_answered = AsyncMock()
        conn._handle_inbound_stasis_start = AsyncMock()
        conn._handle_stasis_start = AsyncMock()

        await conn._handle_event(
            _stasis_start(state="Up", args=["transfer", "tid-1"])
        )
        await _drain_tasks()

        conn._handle_destination_answered.assert_awaited_once_with("tid-1", "chan-1")
        conn._handle_inbound_stasis_start.assert_not_awaited()
        conn._handle_stasis_start.assert_not_awaited()

    async def test_incomplete_workflow_args_are_dropped_not_treated_inbound(self):
        # Partial args mean a malformed originate, not an inbound call — no
        # workflow run should be created for it.
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=False)
        conn._handle_inbound_stasis_start = AsyncMock()
        conn._handle_stasis_start = AsyncMock()

        await conn._handle_event(_stasis_start(state="Up", args=["workflow_id=2"]))
        await _drain_tasks()

        conn._handle_inbound_stasis_start.assert_not_awaited()
        conn._handle_stasis_start.assert_not_awaited()

    async def test_ext_channel_with_pending_bridge_completes_bridge(self):
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=True)
        pending = {"caller_channel_id": "caller-1", "workflow_run_id": "42"}
        conn._pop_pending_bridge = AsyncMock(return_value=pending)
        conn._complete_bridge_after_ext_ready = AsyncMock()
        conn._handle_inbound_stasis_start = AsyncMock()

        await conn._handle_event(_stasis_start(channel_id="ext-1", state="Up"))
        await _drain_tasks()

        conn._complete_bridge_after_ext_ready.assert_awaited_once_with("ext-1", pending)
        conn._handle_inbound_stasis_start.assert_not_awaited()


class TestSpawnTaskRetention:
    async def test_spawn_holds_reference_until_done(self):
        # The event loop keeps only weak refs to tasks; _spawn must hold a
        # strong one while the handler runs and release it afterwards.
        conn = _make_conn()
        started = asyncio.Event()
        release = asyncio.Event()

        async def handler():
            started.set()
            await release.wait()

        task = conn._spawn(handler())
        await started.wait()
        assert task in conn._event_tasks

        release.set()
        await task
        await _drain_tasks()  # let the done callback run
        assert task not in conn._event_tasks

    async def test_handle_event_routes_through_spawn(self):
        # Routing must go through _spawn so handlers are tracked.
        conn = _make_conn()
        conn._is_ext_channel = AsyncMock(return_value=False)
        conn._handle_inbound_stasis_start = AsyncMock()
        spawned = []
        original_spawn = conn._spawn
        conn._spawn = lambda coro: spawned.append(original_spawn(coro)) or spawned[-1]

        await conn._handle_event(_stasis_start(args=[]))
        await _drain_tasks()

        assert len(spawned) == 1


class TestSetupFailureCleanup:
    def _conn_for_stasis_start(self, monkeypatch) -> ARIConnection:
        conn = _make_conn()
        conn._set_channel_run = AsyncMock()
        conn._mark_ext_channel = AsyncMock()
        conn._set_pending_bridge = AsyncMock()
        conn._pop_pending_bridge = AsyncMock()
        conn._delete_channel = AsyncMock()
        monkeypatch.setattr(
            ari_manager_module.db_client, "update_workflow_run", AsyncMock()
        )
        return conn

    async def test_ext_media_failure_hangs_up_caller(self, monkeypatch):
        # The caller is already answered; leaving the channel up after a
        # failed externalMedia POST means dead air until they hang up.
        conn = self._conn_for_stasis_start(monkeypatch)
        conn._create_external_media = AsyncMock(return_value="")

        await conn._handle_stasis_start("caller-1", "Up", "42", "2", "3")

        deleted = {c.args[0] for c in conn._delete_channel.await_args_list}
        assert "caller-1" in deleted
        conn._pop_pending_bridge.assert_awaited()

    async def test_channel_id_mismatch_hangs_up_caller_and_rogue_ext(
        self, monkeypatch
    ):
        # Asterisk ignored our channelId: the pending-bridge entry will never
        # be consumed, so both the caller and the rogue ext leg must die.
        conn = self._conn_for_stasis_start(monkeypatch)
        conn._create_external_media = AsyncMock(return_value="rogue-ext")

        await conn._handle_stasis_start("caller-1", "Up", "42", "2", "3")

        deleted = {c.args[0] for c in conn._delete_channel.await_args_list}
        assert {"caller-1", "rogue-ext"} <= deleted

    async def test_unexpected_error_hangs_up_caller(self, monkeypatch):
        conn = self._conn_for_stasis_start(monkeypatch)
        conn._create_external_media = AsyncMock(side_effect=RuntimeError("boom"))

        await conn._handle_stasis_start("caller-1", "Up", "42", "2", "3")

        deleted = {c.args[0] for c in conn._delete_channel.await_args_list}
        assert "caller-1" in deleted

    async def test_bridge_failure_hangs_up_both_legs(self):
        conn = _make_conn()
        conn._create_bridge_and_add_channels = AsyncMock(return_value="")
        conn._delete_channel = AsyncMock()

        await conn._complete_bridge_after_ext_ready(
            "ext-1", {"caller_channel_id": "caller-1", "workflow_run_id": "42"}
        )

        deleted = {c.args[0] for c in conn._delete_channel.await_args_list}
        assert deleted == {"caller-1", "ext-1"}

    async def test_abort_survives_delete_failures(self):
        # A hangup that itself fails must not raise out of the abort path —
        # the second leg should still be attempted.
        conn = _make_conn()
        conn._delete_channel = AsyncMock(side_effect=RuntimeError("ari down"))

        await conn._abort_call_setup("caller-1", "ext-1")

        assert conn._delete_channel.await_count == 2


class TestStasisEndTeardown:
    async def test_full_teardown_includes_destination_leg(self, monkeypatch):
        # After a completed transfer the bridge holds caller + destination;
        # when the caller hangs up, the destination must be hung up too.
        conn = _make_conn()
        run = SimpleNamespace(
            gathered_context={
                "call_id": "caller-1",
                "ext_channel_id": "ext-1",
                "destination_channel_id": "dest-1",
                "bridge_id": "bridge-1",
                "transfer_state": "complete",
            }
        )
        monkeypatch.setattr(
            ari_manager_module.db_client,
            "get_workflow_run_by_id",
            AsyncMock(return_value=run),
        )
        conn._delete_bridge = AsyncMock()
        conn._delete_channel = AsyncMock()
        conn._delete_channel_run = AsyncMock()
        conn._delete_ext_channel = AsyncMock()

        await conn._handle_stasis_end("caller-1", "42")

        conn._delete_bridge.assert_awaited_once_with("bridge-1")
        deleted = {c.args[0] for c in conn._delete_channel.await_args_list}
        assert deleted == {"ext-1", "dest-1"}, "caller already ended, others torn down"
        cleaned_keys = set(conn._delete_channel_run.await_args_list[0].args)
        assert {"caller-1", "ext-1", "dest-1"} <= cleaned_keys

    async def test_ext_stasis_end_during_transfer_preserves_bridge(self, monkeypatch):
        # While a transfer is in progress, the ext leg's StasisEnd must not
        # tear down the caller-destination bridge.
        conn = _make_conn()
        run = SimpleNamespace(
            gathered_context={
                "call_id": "caller-1",
                "ext_channel_id": "ext-1",
                "destination_channel_id": "dest-1",
                "bridge_id": "bridge-1",
                "transfer_state": "in-progress",
            }
        )
        monkeypatch.setattr(
            ari_manager_module.db_client,
            "get_workflow_run_by_id",
            AsyncMock(return_value=run),
        )
        update_mock = AsyncMock()
        monkeypatch.setattr(
            ari_manager_module.db_client, "update_workflow_run", update_mock
        )
        conn._delete_bridge = AsyncMock()
        conn._delete_channel = AsyncMock()
        conn._delete_channel_run = AsyncMock()
        conn._delete_ext_channel = AsyncMock()

        await conn._handle_stasis_end("ext-1", "42")

        conn._delete_bridge.assert_not_awaited()
        conn._delete_channel.assert_not_awaited()
        assert run.gathered_context["transfer_state"] == "complete"
