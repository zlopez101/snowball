import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import (
    ActionLogStatus,
    ActionOutcome,
    ActionTemplate,
    ActionType,
    Campaign,
    CampaignCreate,
    CampaignStatus,
    DailyActionPlan,
    OfficeType,
    RepresentativeTarget,
    UserActionLog,
    VisibilityMode,
)
from tests.utils.user import create_random_user


def test_read_platform_impact_returns_aggregate_metrics(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    baseline_response = client.get(
        f"{settings.API_V1_STR}/impact/platform?window=7d",
        headers=normal_user_token_headers,
    )
    assert baseline_response.status_code == 200
    baseline_total = baseline_response.json()["total_actions"]

    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/?status=active",
        headers=normal_user_token_headers,
    )
    campaign_id = uuid.UUID(campaigns_response.json()["data"][0]["id"])

    me_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    current_user_id = uuid.UUID(me_response.json()["id"])
    second_user = create_random_user(db)

    db.add(
        UserActionLog(
            user_id=current_user_id,
            campaign_id=campaign_id,
            action_type=ActionType.CALL,
            status=ActionLogStatus.COMPLETED,
            outcome=ActionOutcome.ANSWERED,
            confidence_score=4,
        )
    )
    db.add(
        UserActionLog(
            user_id=second_user.id,
            campaign_id=campaign_id,
            action_type=ActionType.EMAIL,
            status=ActionLogStatus.SKIPPED,
            outcome=ActionOutcome.SENT,
            confidence_score=3,
        )
    )
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/impact/platform?window=7d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["window_days"] == 7
    assert payload["total_actions"] >= baseline_total + 2
    assert payload["completed_actions"] >= 1
    assert payload["skipped_actions"] >= 1
    assert payload["calls"] >= 1
    assert payload["emails"] >= 1
    assert payload["unique_participants"] >= 2
    assert payload["participant_range"] in {"1-9", "10-49", "50-99", "100+", "0"}


def test_read_campaign_impact_returns_only_campaign_logs(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"impact-{uuid.uuid4().hex[:8]}",
            title="Impact Campaign",
            description="Campaign for impact route tests",
            policy_topic="test",
            status=CampaignStatus.ACTIVE,
        )
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    me_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    current_user_id = uuid.UUID(me_response.json()["id"])

    db.add(
        UserActionLog(
            user_id=current_user_id,
            campaign_id=campaign.id,
            action_type=ActionType.CALL,
            status=ActionLogStatus.COMPLETED,
            outcome=ActionOutcome.ANSWERED,
            confidence_score=4,
        )
    )
    db.add(
        UserActionLog(
            user_id=current_user_id,
            campaign_id=campaign.id,
            action_type=ActionType.EMAIL,
            status=ActionLogStatus.COMPLETED,
            outcome=ActionOutcome.SENT,
            confidence_score=5,
        )
    )
    db.add(
        UserActionLog(
            user_id=current_user_id,
            campaign_id=campaign.id,
            action_type=ActionType.CALL,
            status=ActionLogStatus.SKIPPED,
            outcome=ActionOutcome.UNKNOWN,
            confidence_score=2,
        )
    )
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/impact/campaign/{campaign.id}?window=7d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["campaign_id"] == str(campaign.id)
    assert payload["campaign_title"] == campaign.title
    assert payload["total_actions"] == 3
    assert payload["completed_actions"] == 2
    assert payload["skipped_actions"] == 1
    assert payload["calls"] == 2
    assert payload["emails"] == 1
    assert payload["unique_participants"] == 1
    assert payload["participant_range"] == "1-9"


def test_read_campaign_impact_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/impact/campaign/{uuid.uuid4()}?window=7d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Campaign not found"


def test_read_representative_impact_returns_target_scoped_metrics(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/?status=active",
        headers=normal_user_token_headers,
    )
    assert campaigns_response.status_code == 200
    campaign_id = campaigns_response.json()["data"][0]["id"]

    targets_response = client.get(
        f"{settings.API_V1_STR}/campaigns/{campaign_id}/targets",
        headers=normal_user_token_headers,
    )
    assert targets_response.status_code == 200
    target_id = targets_response.json()["data"][0]["id"]

    templates_response = client.get(
        f"{settings.API_V1_STR}/campaigns/{campaign_id}/templates",
        headers=normal_user_token_headers,
    )
    assert templates_response.status_code == 200
    template = next(
        item
        for item in templates_response.json()["data"]
        if item["target_id"] == target_id
    )

    create_response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=normal_user_token_headers,
        json={
            "campaign_id": campaign_id,
            "target_id": target_id,
            "template_id": template["id"],
            "action_type": template["action_type"],
            "status": "completed",
            "outcome": "answered",
            "confidence_score": 4,
        },
    )
    assert create_response.status_code == 200

    response = client.get(
        f"{settings.API_V1_STR}/impact/representative/{target_id}?window=30d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["total_actions"] >= 1
    assert payload["completed_actions"] >= 1
    assert payload["campaign_id"] == campaign_id


def test_read_representative_impact_not_found(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/impact/representative/{uuid.uuid4()}?window=30d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Representative target not found"


def test_share_card_is_private_by_default(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/impact/me/share-card?window=7d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["shareable"] is False
    assert payload["display_name"] is None
    assert payload["visibility_mode"] == "private"
    assert payload["period_label"] == "last_7_days"


def test_share_card_includes_username_only_for_public_opt_in(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    me_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    assert me_response.status_code == 200
    user_id = uuid.UUID(me_response.json()["id"])

    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"share-card-{uuid.uuid4().hex[:8]}",
            title="Share Card Campaign",
            description="Campaign for share card tests",
            policy_topic="privacy",
            status=CampaignStatus.ACTIVE,
        )
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    target = RepresentativeTarget(
        campaign_id=campaign.id,
        office_type=OfficeType.HOUSE,
        office_name="Rep. Test",
        state_code="TX",
        district_code="07",
    )
    db.add(target)
    db.commit()
    db.refresh(target)

    template = ActionTemplate(
        campaign_id=campaign.id,
        target_id=target.id,
        action_type=ActionType.CALL,
        title="Call your representative",
        script_text="Please support this campaign.",
        estimated_minutes=3,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    plan = DailyActionPlan(
        user_id=user_id,
        campaign_id=campaign.id,
        target_actions_per_day=1,
        active_weekdays_mask="1111111",
        is_active=True,
    )
    db.add(plan)
    db.commit()

    update_response = client.patch(
        f"{settings.API_V1_STR}/profile/me",
        headers=normal_user_token_headers,
        json={"visibility_mode": "public_opt_in"},
    )
    assert update_response.status_code == 200
    username = update_response.json()["username"]

    privacy_response = client.patch(
        f"{settings.API_V1_STR}/privacy/me",
        headers=normal_user_token_headers,
        json={"allow_shareable_card": True},
    )
    assert privacy_response.status_code == 200

    log_response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=normal_user_token_headers,
        json={
            "campaign_id": str(campaign.id),
            "target_id": str(target.id),
            "template_id": str(template.id),
            "action_type": "call",
            "status": "completed",
            "outcome": "answered",
            "confidence_score": 4,
        },
    )
    assert log_response.status_code == 200

    response = client.get(
        f"{settings.API_V1_STR}/impact/me/share-card?window=7d",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["shareable"] is True
    assert payload["visibility_mode"] == VisibilityMode.PUBLIC_OPT_IN.value
    assert payload["display_name"] == username
