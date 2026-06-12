"""Unit tests for CallTransferManager context storage and lookup.

The by-caller index (``transfer:by_caller:{call_sid}``) replaces the previous
KEYS scan over ``transfer:context:*`` — these tests pin the index lifecycle:
written on store, resolved on lookup, dropped on remove (but only while it
still points at the transfer being removed).
"""

from api.services.telephony.call_transfer_manager import CallTransferManager
from api.services.telephony.transfer_event_protocol import TransferContext


class _FakeRedis:
    """Minimal async stand-in for the redis client methods the manager uses.

    Deliberately has no keys()/scan(): a lookup that regresses to a keyspace
    scan fails loudly here.
    """

    def __init__(self):
        self.store = {}

    async def setex(self, key, ttl, value):
        self.store[key] = value

    async def get(self, key):
        return self.store.get(key)

    async def delete(self, *keys):
        for key in keys:
            self.store.pop(key, None)


def _context(transfer_id="t-1", caller="caller-1") -> TransferContext:
    return TransferContext(
        transfer_id=transfer_id,
        call_sid=None,
        target_number="PJSIP/6001",
        tool_uuid="tool-1",
        original_call_sid=caller,
        conference_name=f"transfer-{caller}",
        initiated_at=1718000000.0,
    )


class TestFindTransferContextForCall:
    async def test_lookup_resolves_via_index(self):
        manager = CallTransferManager(redis_client=_FakeRedis())
        await manager.store_transfer_context(_context())

        found = await manager.find_transfer_context_for_call("caller-1")

        assert found is not None
        assert found.transfer_id == "t-1"

    async def test_lookup_unknown_caller_returns_none(self):
        manager = CallTransferManager(redis_client=_FakeRedis())
        assert await manager.find_transfer_context_for_call("nope") is None

    async def test_restore_overwrites_index_with_latest_transfer(self):
        # The engine stores the context twice (initial + call_sid update);
        # the second store must keep the index pointing at the same transfer.
        manager = CallTransferManager(redis_client=_FakeRedis())
        ctx = _context()
        await manager.store_transfer_context(ctx)
        ctx.call_sid = "dest-1"
        await manager.store_transfer_context(ctx)

        found = await manager.find_transfer_context_for_call("caller-1")
        assert found is not None
        assert found.call_sid == "dest-1"


class TestRemoveTransferContext:
    async def test_remove_drops_context_and_index(self):
        fake = _FakeRedis()
        manager = CallTransferManager(redis_client=fake)
        await manager.store_transfer_context(_context())

        await manager.remove_transfer_context("t-1")

        assert await manager.find_transfer_context_for_call("caller-1") is None
        assert fake.store == {}

    async def test_remove_of_stale_transfer_keeps_newer_index(self):
        # Two transfers for the same caller: removing the older one must not
        # drop the index entry now owned by the newer one.
        manager = CallTransferManager(redis_client=_FakeRedis())
        await manager.store_transfer_context(_context(transfer_id="t-old"))
        await manager.store_transfer_context(_context(transfer_id="t-new"))

        await manager.remove_transfer_context("t-old")

        found = await manager.find_transfer_context_for_call("caller-1")
        assert found is not None
        assert found.transfer_id == "t-new"

    async def test_context_without_caller_id_skips_index(self):
        fake = _FakeRedis()
        manager = CallTransferManager(redis_client=fake)
        await manager.store_transfer_context(_context(caller=""))

        assert not [k for k in fake.store if k.startswith("transfer:by_caller:")]
