import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ActionType,
    Campaign,
    ImpactPublic,
    ImpactShareCardPublic,
    RepresentativeTarget,
    UserActionLog,
    UserPrivacySettings,
    UserProfile,
    VisibilityMode,
)

router = APIRouter(prefix="/impact", tags=["impact"])


def _window_start(window: str) -> tuple[int, datetime]:
    value = window.strip().lower()
    if not value.endswith("d") or not value[:-1].isdigit():
        raise HTTPException(status_code=400, detail="Window must be like 7d or 30d")
    days = int(value[:-1])
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="Window days must be between 1 and 365")
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return days, start


def _participant_range(count: int) -> str:
    if count == 0:
        return "0"
    if count < 10:
        return "1-9"
    if count < 50:
        return "10-49"
    if count < 100:
        return "50-99"
    return "100+"


def _build_impact(logs: list[UserActionLog], *, window_days: int) -> ImpactPublic:
    completed_actions = sum(1 for item in logs if item.status.value == "completed")
    skipped_actions = sum(1 for item in logs if item.status.value == "skipped")
    calls = sum(1 for item in logs if item.action_type == ActionType.CALL)
    emails = sum(1 for item in logs if item.action_type == ActionType.EMAIL)
    boycotts = sum(1 for item in logs if item.action_type == ActionType.BOYCOTT)
    events = sum(1 for item in logs if item.action_type == ActionType.EVENT)
    unique_participants = len({item.user_id for item in logs})
    last_action_at = max((item.created_at for item in logs if item.created_at), default=None)

    return ImpactPublic(
        window_days=window_days,
        total_actions=len(logs),
        completed_actions=completed_actions,
        skipped_actions=skipped_actions,
        calls=calls,
        emails=emails,
        boycotts=boycotts,
        events=events,
        unique_participants=unique_participants,
        participant_range=_participant_range(unique_participants),
        last_action_at=last_action_at,
    )


def _build_share_card(
    *,
    logs: list[UserActionLog],
    window_days: int,
    visibility_mode: VisibilityMode,
    allow_shareable_card: bool,
    username: str,
) -> ImpactShareCardPublic:
    completed_actions = sum(1 for item in logs if item.status.value == "completed")
    calls = sum(1 for item in logs if item.action_type == ActionType.CALL)
    emails = sum(1 for item in logs if item.action_type == ActionType.EMAIL)
    shareable = allow_shareable_card and visibility_mode == VisibilityMode.PUBLIC_OPT_IN
    display_name = username if shareable else None
    message = (
        "Shareable card enabled. Personal details are limited to your opted-in username."
        if shareable
        else "Share card is privacy-safe only. Enable public opt-in visibility and shareable cards in settings to include your username."
    )
    return ImpactShareCardPublic(
        window_days=window_days,
        shareable=shareable,
        visibility_mode=visibility_mode,
        display_name=display_name,
        period_label=f"last_{window_days}_days",
        total_actions=len(logs),
        completed_actions=completed_actions,
        calls=calls,
        emails=emails,
        message=message,
    )


@router.get("/platform", response_model=ImpactPublic)
def read_platform_impact(
    session: SessionDep,
    _current_user: CurrentUser,
    window: str = Query(default="7d"),
) -> Any:
    window_days, window_start = _window_start(window)
    logs = session.exec(
        select(UserActionLog).where(UserActionLog.created_at >= window_start)
    ).all()
    return _build_impact(logs, window_days=window_days)


@router.get("/campaign/{campaign_id}", response_model=ImpactPublic)
def read_campaign_impact(
    session: SessionDep,
    _current_user: CurrentUser,
    campaign_id: uuid.UUID,
    window: str = Query(default="30d"),
) -> Any:
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    window_days, window_start = _window_start(window)
    logs = session.exec(
        select(UserActionLog).where(
            UserActionLog.created_at >= window_start,
            UserActionLog.campaign_id == campaign_id,
        )
    ).all()
    impact = _build_impact(logs, window_days=window_days)
    impact.campaign_id = campaign.id
    impact.campaign_title = campaign.title
    return impact


@router.get("/representative/{target_id}", response_model=ImpactPublic)
def read_representative_impact(
    session: SessionDep,
    _current_user: CurrentUser,
    target_id: uuid.UUID,
    window: str = Query(default="30d"),
) -> Any:
    target = session.get(RepresentativeTarget, target_id)
    if not target:
        raise HTTPException(status_code=404, detail="Representative target not found")

    window_days, window_start = _window_start(window)
    logs = session.exec(
        select(UserActionLog).where(
            UserActionLog.created_at >= window_start,
            UserActionLog.target_id == target_id,
        )
    ).all()
    impact = _build_impact(logs, window_days=window_days)
    campaign = session.get(Campaign, target.campaign_id)
    if campaign:
        impact.campaign_id = campaign.id
        impact.campaign_title = campaign.title
    return impact


@router.get("/me/share-card", response_model=ImpactShareCardPublic)
def read_my_share_card(
    session: SessionDep,
    current_user: CurrentUser,
    window: str = Query(default="7d"),
) -> Any:
    profile = session.get(UserProfile, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")

    privacy = session.get(UserPrivacySettings, current_user.id)
    allow_shareable_card = privacy.allow_shareable_card if privacy else False

    window_days, window_start = _window_start(window)
    logs = session.exec(
        select(UserActionLog).where(
            UserActionLog.user_id == current_user.id,
            UserActionLog.created_at >= window_start,
        )
    ).all()
    return _build_share_card(
        logs=logs,
        window_days=window_days,
        visibility_mode=profile.visibility_mode,
        allow_shareable_card=allow_shareable_card,
        username=profile.username,
    )
