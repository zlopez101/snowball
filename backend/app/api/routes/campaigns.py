import uuid
from typing import Any

from fastapi import APIRouter, HTTPException
from sqlmodel import col, func, select

from app.api.deps import CurrentUser, SessionDep
from app.models import (
    ActionTemplate,
    ActionTemplatesPublic,
    Campaign,
    CampaignPublic,
    CampaignsPublic,
    CampaignStatus,
    RepresentativeTarget,
    RepresentativeTargetsPublic,
)

router = APIRouter(prefix="/campaigns", tags=["campaigns"])


@router.get("/", response_model=CampaignsPublic)
def read_campaigns(
    session: SessionDep,
    _current_user: CurrentUser,
    skip: int = 0,
    limit: int = 100,
    status: CampaignStatus | None = None,
) -> Any:
    """
    Retrieve campaigns.
    """
    filters = []
    if status is not None:
        filters.append(Campaign.status == status)

    count_statement = select(func.count()).select_from(Campaign)
    statement = select(Campaign).order_by(col(Campaign.created_at).desc())
    if filters:
        count_statement = count_statement.where(*filters)
        statement = statement.where(*filters)

    count = session.exec(count_statement).one()
    campaigns = session.exec(statement.offset(skip).limit(limit)).all()
    return CampaignsPublic(data=campaigns, count=count)


@router.get("/{campaign_id}", response_model=CampaignPublic)
def read_campaign(
    session: SessionDep,
    _current_user: CurrentUser,
    campaign_id: uuid.UUID,
) -> Any:
    """
    Get campaign by ID.
    """
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")
    return campaign


@router.get("/{campaign_id}/targets", response_model=RepresentativeTargetsPublic)
def read_campaign_targets(
    session: SessionDep,
    _current_user: CurrentUser,
    campaign_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve representative targets for a campaign.
    """
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    count_statement = (
        select(func.count())
        .select_from(RepresentativeTarget)
        .where(RepresentativeTarget.campaign_id == campaign_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(RepresentativeTarget)
        .where(RepresentativeTarget.campaign_id == campaign_id)
        .order_by(col(RepresentativeTarget.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    targets = session.exec(statement).all()
    return RepresentativeTargetsPublic(data=targets, count=count)


@router.get("/{campaign_id}/templates", response_model=ActionTemplatesPublic)
def read_campaign_templates(
    session: SessionDep,
    _current_user: CurrentUser,
    campaign_id: uuid.UUID,
    skip: int = 0,
    limit: int = 100,
) -> Any:
    """
    Retrieve action templates for a campaign.
    """
    campaign = session.get(Campaign, campaign_id)
    if not campaign:
        raise HTTPException(status_code=404, detail="Campaign not found")

    count_statement = (
        select(func.count())
        .select_from(ActionTemplate)
        .where(ActionTemplate.campaign_id == campaign_id)
    )
    count = session.exec(count_statement).one()
    statement = (
        select(ActionTemplate)
        .where(ActionTemplate.campaign_id == campaign_id)
        .order_by(col(ActionTemplate.created_at).desc())
        .offset(skip)
        .limit(limit)
    )
    templates = session.exec(statement).all()
    return ActionTemplatesPublic(data=templates, count=count)
