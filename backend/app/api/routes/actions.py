from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ActionStatsPublic,
    ActionTemplate,
    ActionType,
    Campaign,
    DailyActionPlan,
    RepresentativeTarget,
    TodayActionPublic,
    TodayActionsPublic,
    UserActionLog,
    UserActionLogCreate,
    UserActionLogPublic,
    UserActionLogsPublic,
)

router = APIRouter(prefix="/actions", tags=["actions"])


def _window_start(window: str) -> tuple[int, datetime]:
    value = window.strip().lower()
    if not value.endswith("d") or not value[:-1].isdigit():
        raise HTTPException(status_code=400, detail="Window must be like 7d or 30d")
    days = int(value[:-1])
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="Window days must be between 1 and 365")
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return days, start


@router.get("/today", response_model=TodayActionsPublic)
def read_actions_today(session: SessionDep, current_user: CurrentUser) -> Any:
    weekday = datetime.now(timezone.utc).weekday()
    plans = session.exec(
        select(DailyActionPlan).where(
            DailyActionPlan.user_id == current_user.id,
            DailyActionPlan.is_active.is_(True),
        )
    ).all()

    actions: list[TodayActionPublic] = []
    for plan in plans:
        if len(plan.active_weekdays_mask) != 7 or plan.active_weekdays_mask[weekday] != "1":
            continue
        campaign = session.get(Campaign, plan.campaign_id)
        if not campaign:
            continue
        templates = session.exec(
            select(ActionTemplate)
            .where(ActionTemplate.campaign_id == plan.campaign_id)
            .order_by(col(ActionTemplate.created_at).desc())
            .limit(plan.target_actions_per_day)
        ).all()
        for template in templates:
            actions.append(
                TodayActionPublic(
                    campaign_id=campaign.id,
                    campaign_title=campaign.title,
                    template_id=template.id,
                    target_id=template.target_id,
                    action_type=template.action_type,
                    title=template.title,
                    estimated_minutes=template.estimated_minutes,
                )
            )

    return TodayActionsPublic(data=actions, count=len(actions))


@router.post("/log", response_model=UserActionLogPublic)
def create_action_log(
    *, session: SessionDep, current_user: CurrentUser, body: UserActionLogCreate
) -> Any:
    campaign = session.get(Campaign, body.campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    if body.target_id is not None:
        target = session.get(RepresentativeTarget, body.target_id)
        if target and target.campaign_id != body.campaign_id:
            raise HTTPException(status_code=400, detail="Target does not belong to campaign")

    if body.template_id is not None:
        template = session.get(ActionTemplate, body.template_id)
        if template is None:
            raise HTTPException(status_code=404, detail="Action template not found")
        if template.campaign_id != body.campaign_id:
            raise HTTPException(
                status_code=400, detail="Action template does not belong to campaign"
            )

    action_log = UserActionLog.model_validate(body, update={"user_id": current_user.id})
    session.add(action_log)
    session.commit()
    session.refresh(action_log)
    return action_log


@router.get("/me", response_model=UserActionLogsPublic)
def read_my_actions(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    count_statement = (
        select(func.count())
        .select_from(UserActionLog)
        .where(UserActionLog.user_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(UserActionLog)
        .where(UserActionLog.user_id == current_user.id)
        .order_by(col(UserActionLog.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    logs = session.exec(statement).all()
    return UserActionLogsPublic(data=logs, count=count)


@router.get("/me/stats", response_model=ActionStatsPublic)
def read_my_action_stats(
    session: SessionDep,
    current_user: CurrentUser,
    window: str = Query(default="7d"),
) -> Any:
    window_days, window_start = _window_start(window)
    logs = session.exec(
        select(UserActionLog).where(
            UserActionLog.user_id == current_user.id,
            UserActionLog.created_at >= window_start,
        )
    ).all()

    completed_actions = sum(1 for item in logs if item.status.value == "completed")
    skipped_actions = sum(1 for item in logs if item.status.value == "skipped")
    calls = sum(1 for item in logs if item.action_type == ActionType.CALL)
    emails = sum(1 for item in logs if item.action_type == ActionType.EMAIL)
    boycotts = sum(1 for item in logs if item.action_type == ActionType.BOYCOTT)
    events = sum(1 for item in logs if item.action_type == ActionType.EVENT)
    last_action_at = max((item.created_at for item in logs if item.created_at), default=None)

    return ActionStatsPublic(
        window_days=window_days,
        total_actions=len(logs),
        completed_actions=completed_actions,
        skipped_actions=skipped_actions,
        calls=calls,
        emails=emails,
        boycotts=boycotts,
        events=events,
        last_action_at=last_action_at,
    )
