import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.models import (
    Message,
    Referral,
    ReferralAssistsPublic,
    ReferralClaimCreate,
    ReferralLinkCreate,
    ReferralPublic,
    ReferralsPublic,
    UserActionLog,
    UserPrivacySettings,
)

router = APIRouter(prefix="/referrals", tags=["referrals"])


def _window_start(window: str) -> tuple[int, datetime]:
    value = window.strip().lower()
    if not value.endswith("d") or not value[:-1].isdigit():
        raise HTTPException(status_code=400, detail="Window must be like 7d or 30d")
    days = int(value[:-1])
    if days <= 0 or days > 365:
        raise HTTPException(status_code=400, detail="Window days must be between 1 and 365")
    start = datetime.now(timezone.utc) - timedelta(days=days)
    return days, start


def _invite_url(code: str) -> str:
    return f"{settings.FRONTEND_HOST}/signup?ref={code}"


@router.post("/link", response_model=ReferralPublic)
def create_referral_link(
    *, session: SessionDep, current_user: CurrentUser, body: ReferralLinkCreate
) -> Any:
    privacy = session.get(UserPrivacySettings, current_user.id)
    if privacy is not None and not privacy.allow_referral_tracking:
        raise HTTPException(
            status_code=403, detail="Referral tracking is disabled in your privacy settings"
        )

    code = secrets.token_urlsafe(8)
    referral = Referral(
        referrer_user_id=current_user.id,
        code=code,
        channel=body.channel,
    )
    session.add(referral)
    session.commit()
    session.refresh(referral)

    return ReferralPublic(
        id=referral.id,
        referrer_user_id=referral.referrer_user_id,
        referred_user_id=referral.referred_user_id,
        code=referral.code,
        channel=referral.channel,
        invite_url=_invite_url(referral.code),
        created_at=referral.created_at,
    )


@router.post("/claim", response_model=Message)
def claim_referral(
    *, session: SessionDep, current_user: CurrentUser, body: ReferralClaimCreate
) -> Any:
    referral = session.exec(select(Referral).where(Referral.code == body.code)).first()
    if referral is None:
        raise HTTPException(status_code=404, detail="Referral code not found")

    if referral.referrer_user_id == current_user.id:
        raise HTTPException(status_code=400, detail="You cannot claim your own referral code")

    existing_claim = session.exec(
        select(Referral).where(Referral.referred_user_id == current_user.id)
    ).first()
    if existing_claim:
        raise HTTPException(status_code=409, detail="User has already claimed a referral")

    if referral.referred_user_id is not None:
        raise HTTPException(status_code=409, detail="Referral code was already claimed")

    referral.referred_user_id = current_user.id
    session.add(referral)
    session.commit()

    return Message(message="Referral claimed")


@router.get("/me", response_model=ReferralsPublic)
def read_my_referrals(
    session: SessionDep,
    current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    count_statement = (
        select(func.count())
        .select_from(Referral)
        .where(Referral.referrer_user_id == current_user.id)
    )
    count = session.exec(count_statement).one()
    rows = session.exec(
        select(Referral)
        .where(Referral.referrer_user_id == current_user.id)
        .order_by(col(Referral.created_at).desc())
        .offset(skip)
        .limit(limit)
    ).all()
    data = [
        ReferralPublic(
            id=row.id,
            referrer_user_id=row.referrer_user_id,
            referred_user_id=row.referred_user_id,
            code=row.code,
            channel=row.channel,
            invite_url=_invite_url(row.code),
            created_at=row.created_at,
        )
        for row in rows
    ]
    return ReferralsPublic(data=data, count=count)


@router.get("/me/assists", response_model=ReferralAssistsPublic)
def read_my_referral_assists(
    session: SessionDep, current_user: CurrentUser, window: str = Query(default="7d")
) -> Any:
    window_days, window_start = _window_start(window)
    referred_ids = session.exec(
        select(Referral.referred_user_id).where(
            Referral.referrer_user_id == current_user.id,
            Referral.referred_user_id.is_not(None),
            Referral.created_at >= window_start,
        )
    ).all()
    filtered_ids = [user_id for user_id in referred_ids if user_id is not None]
    if not filtered_ids:
        return ReferralAssistsPublic(
            window_days=window_days, recruited_users=0, assisted_actions=0
        )

    recruited_users = len(filtered_ids)
    assisted_actions = session.exec(
        select(func.count())
        .select_from(UserActionLog)
        .where(
            UserActionLog.user_id.in_(filtered_ids),
            UserActionLog.created_at >= window_start,
        )
    ).one()
    return ReferralAssistsPublic(
        window_days=window_days,
        recruited_users=recruited_users,
        assisted_actions=assisted_actions,
    )
