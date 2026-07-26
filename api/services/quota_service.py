"""Quota gate for outbound work (calls, chats, campaign dispatch).

Every call path routes through here before starting a run. It used to meter
Dograh's hosted credits; we now run entirely on our own provider keys, so
there is nothing left to meter and every request passes.

The seam is kept deliberately: org-level limits (concurrent calls, minutes,
internal budgets) belong in this one place rather than in each of the eleven
call sites that already ask permission here.
"""

from dataclasses import dataclass

from api.db import db_client
from api.db.models import UserModel


@dataclass
class QuotaCheckResult:
    """Result of a quota check."""

    has_quota: bool
    error_message: str = ""
    error_code: str = ""


async def check_quota(
    user: UserModel, workflow_id: int | None = None
) -> QuotaCheckResult:
    """Decide whether this user may start a run.

    Args:
        user: The user the run belongs to.
        workflow_id: Workflow the run will use. Unused today; kept so future
            per-workflow limits don't have to touch every call site.

    Returns:
        QuotaCheckResult — currently always allowing.
    """
    return QuotaCheckResult(has_quota=True)


async def check_quota_by_user_id(
    user_id: int, workflow_id: int | None = None
) -> QuotaCheckResult:
    """Same as :func:`check_quota`, for call paths that only hold a user id."""
    user = await db_client.get_user_by_id(user_id)
    if not user:
        return QuotaCheckResult(
            has_quota=False,
            error_message="User not found",
        )
    return await check_quota(user, workflow_id=workflow_id)
