from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import Session, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    Campaign,
    CampaignStatus,
    DailyActionPlan,
    OnboardingComplete,
    OnboardingCompletePublic,
    UserPrivacySettings,
    UserPrivacySettingsPublic,
    UserPrivacySettingsUpdate,
    UserProfile,
    UserProfilePublic,
    UserProfileUpdate,
    VisibilityMode,
)

router = APIRouter(tags=["onboarding"])


def _upsert_profile(
    session: Session,
    *,
    current_user_id: Any,
    profile_in: UserProfileUpdate,
) -> UserProfile:
    profile = session.get(UserProfile, current_user_id)

    if profile_in.username is not None:
        existing_username = session.exec(
            select(UserProfile).where(UserProfile.username == profile_in.username)
        ).first()
        if existing_username and existing_username.user_id != current_user_id:
            raise HTTPException(status_code=409, detail="Username is already taken")

    if profile is None:
        if profile_in.username is None:
            raise HTTPException(status_code=400, detail="Username is required")
        profile = UserProfile(
            user_id=current_user_id,
            username=profile_in.username,
            state_code=profile_in.state_code,
            district_code=profile_in.district_code,
            timezone=profile_in.timezone or "America/Chicago",
            visibility_mode=profile_in.visibility_mode or VisibilityMode.PRIVATE,
        )
    else:
        profile.sqlmodel_update(profile_in.model_dump(exclude_unset=True))

    session.add(profile)
    session.commit()
    session.refresh(profile)
    return profile


def _upsert_privacy_settings(
    session: Session,
    *,
    current_user_id: Any,
    privacy_in: UserPrivacySettingsUpdate | None = None,
) -> UserPrivacySettings:
    privacy = session.get(UserPrivacySettings, current_user_id)
    if privacy is None:
        privacy = UserPrivacySettings(user_id=current_user_id)

    if privacy_in is not None:
        privacy.sqlmodel_update(privacy_in.model_dump(exclude_unset=True))

    session.add(privacy)
    session.commit()
    session.refresh(privacy)
    return privacy


@router.post("/onboarding/complete", response_model=OnboardingCompletePublic)
def complete_onboarding(
    *, session: SessionDep, current_user: CurrentUser, body: OnboardingComplete
) -> Any:
    profile = _upsert_profile(
        session,
        current_user_id=current_user.id,
        profile_in=UserProfileUpdate.model_validate(body),
    )
    privacy = _upsert_privacy_settings(session, current_user_id=current_user.id)

    campaign_ids = body.campaign_ids
    if campaign_ids:
        campaigns = session.exec(
            select(Campaign).where(
                Campaign.id.in_(campaign_ids),
                Campaign.status == CampaignStatus.ACTIVE,
            )
        ).all()
        if len(campaigns) != len(set(campaign_ids)):
            raise HTTPException(
                status_code=404,
                detail="One or more selected campaigns were not found",
            )

        existing_plans = session.exec(
            select(DailyActionPlan).where(DailyActionPlan.user_id == current_user.id)
        ).all()
        for plan in existing_plans:
            plan.is_active = False
            session.add(plan)
        session.commit()

        for campaign in campaigns:
            session.add(
                DailyActionPlan(
                    user_id=current_user.id,
                    campaign_id=campaign.id,
                    target_actions_per_day=body.target_actions_per_day,
                    active_weekdays_mask=body.active_weekdays_mask,
                    is_active=True,
                )
            )
        session.commit()

    count_statement = (
        select(func.count())
        .select_from(DailyActionPlan)
        .where(
            DailyActionPlan.user_id == current_user.id,
            DailyActionPlan.is_active.is_(True),
        )
    )
    daily_plans_count = session.exec(count_statement).one()

    return OnboardingCompletePublic(
        profile=UserProfilePublic.model_validate(profile),
        privacy=UserPrivacySettingsPublic.model_validate(privacy),
        daily_plans_count=daily_plans_count,
    )


@router.get("/profile/me", response_model=UserProfilePublic)
def read_profile_me(session: SessionDep, current_user: CurrentUser) -> Any:
    profile = session.get(UserProfile, current_user.id)
    if not profile:
        raise HTTPException(status_code=404, detail="Profile not found")
    return profile


@router.patch("/profile/me", response_model=UserProfilePublic)
def update_profile_me(
    *, session: SessionDep, current_user: CurrentUser, body: UserProfileUpdate
) -> Any:
    profile = _upsert_profile(
        session,
        current_user_id=current_user.id,
        profile_in=body,
    )
    return profile


@router.get("/privacy/me", response_model=UserPrivacySettingsPublic)
def read_privacy_me(session: SessionDep, current_user: CurrentUser) -> Any:
    privacy = session.get(UserPrivacySettings, current_user.id)
    if not privacy:
        privacy = _upsert_privacy_settings(session, current_user_id=current_user.id)
    return privacy


@router.patch("/privacy/me", response_model=UserPrivacySettingsPublic)
def update_privacy_me(
    *, session: SessionDep, current_user: CurrentUser, body: UserPrivacySettingsUpdate
) -> Any:
    privacy = _upsert_privacy_settings(
        session,
        current_user_id=current_user.id,
        privacy_in=body,
    )
    return privacy
