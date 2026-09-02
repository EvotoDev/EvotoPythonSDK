"""Current-user info helpers.

Thin wrapper over the host ``user.info`` RPC; returns a typed
:class:`UserInfo` snapshot so plugins don't have to dig through raw
JSON field names.
"""

from __future__ import annotations

from dataclasses import dataclass

from .core.api_commands import UserCmd
from .core.api_fields import UserField


@dataclass(frozen=True)
class UserInfo:
    """Snapshot of the currently signed-in user.

    Matches the ``user.info`` response one-to-one. Values are provided by
    the host account state, so they stay in sync with the in-app account
    display.

    Attributes:
        user_id: Numeric user id. ``-1`` when not signed in.
        display_name: Human-readable name shown in the app (may be empty).
        email: Account email; empty when the user only bound a phone.
        credits_total: Total credits granted for the current billing period.
        credits_used: Credits already consumed in the current billing period.
        credits_remaining: Credits still available. Mirrors the in-app
            "Remaining" value (the host computes it against the subscription
            snapshot, so it may differ slightly from ``total - used`` due to
            in-flight adjustments).
        has_cloud_space: ``True`` when the account has any cloud storage
            entitlement. When ``False``, the two ``cloud_*`` strings are empty.
        cloud_used_space: Pre-formatted used cloud storage, e.g. ``"118.8GB"``.
            The host returns the display string directly; parse it yourself if
            you need raw bytes.
        cloud_total_space: Pre-formatted total cloud storage, e.g. ``"2.01TB"``.
        next_bill_date: Next billing date in ``yyyy-MM-dd``; empty when no
            subscription is active.
        is_subscribed: ``True`` while a paid subscription is running.
        is_vip: ``True`` when the account holds any VIP tier.
    """

    user_id: int
    display_name: str
    email: str
    credits_total: float
    credits_used: float
    credits_remaining: float
    has_cloud_space: bool
    cloud_used_space: str
    cloud_total_space: str
    next_bill_date: str
    is_subscribed: bool
    is_vip: bool

    @classmethod
    def from_dict(cls, d: dict) -> UserInfo:
        return cls(
            user_id=int(d.get(UserField.USER_ID, -1)),
            display_name=d.get(UserField.DISPLAY_NAME, "") or "",
            email=d.get(UserField.EMAIL, "") or "",
            credits_total=float(d.get(UserField.CREDITS_TOTAL, 0.0) or 0.0),
            credits_used=float(d.get(UserField.CREDITS_USED, 0.0) or 0.0),
            credits_remaining=float(d.get(UserField.CREDITS_REMAINING, 0.0) or 0.0),
            has_cloud_space=bool(d.get(UserField.HAS_CLOUD_SPACE, False)),
            cloud_used_space=d.get(UserField.CLOUD_USED_SPACE, "") or "",
            cloud_total_space=d.get(UserField.CLOUD_TOTAL_SPACE, "") or "",
            next_bill_date=d.get(UserField.NEXT_BILL_DATE, "") or "",
            is_subscribed=bool(d.get(UserField.IS_SUBSCRIBED, False)),
            is_vip=bool(d.get(UserField.IS_VIP, False)),
        )


class UserAPI:
    """Query the currently signed-in user (``user.*`` domain)."""

    def __init__(self, client):
        self._client = client

    def info(self) -> UserInfo:
        """Return a :class:`UserInfo` snapshot of the current user.

        This is a one-shot read: there is no subscription event. Poll when
        you need fresh values (e.g. to watch credits drop during a big export).
        """
        result = self._client.call(UserCmd.INFO, {})
        return UserInfo.from_dict(result)
