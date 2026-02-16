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
    UserActionLog,
)


def test_read_actions_today_returns_planned_templates(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"today-{uuid.uuid4().hex[:8]}",
            title="Today Campaign",
            description="Campaign used for actions today test",
            policy_topic="test",
            status=CampaignStatus.ACTIVE,
        )
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    template = ActionTemplate(
        campaign_id=campaign.id,
        action_type=ActionType.CALL,
        title="Call your representative",
        script_text="Please support this issue.",
        estimated_minutes=2,
    )
    db.add(template)
    db.commit()
    db.refresh(template)

    me_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    user_id = uuid.UUID(me_response.json()["id"])
    plan = DailyActionPlan(
        user_id=user_id,
        campaign_id=campaign.id,
        target_actions_per_day=3,
        active_weekdays_mask="1111111",
        is_active=True,
    )
    db.add(plan)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/actions/today",
        headers=normal_user_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert any(
        row["campaign_id"] == str(campaign.id)
        and row["template_id"] == str(template.id)
        for row in payload["data"]
    )


def test_create_action_log_and_read_stats(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=normal_user_token_headers,
    )
    campaign_id = campaigns_response.json()["data"][0]["id"]

    log_payload = {
        "campaign_id": campaign_id,
        "action_type": "call",
        "status": "completed",
        "outcome": "answered",
        "confidence_score": 4,
    }
    response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=normal_user_token_headers,
        json=log_payload,
    )
    assert response.status_code == 200
    log = response.json()
    assert log["campaign_id"] == campaign_id
    assert log["status"] == ActionLogStatus.COMPLETED.value
    assert log["outcome"] == ActionOutcome.ANSWERED.value

    stats_response = client.get(
        f"{settings.API_V1_STR}/actions/me/stats?window=7d",
        headers=normal_user_token_headers,
    )
    assert stats_response.status_code == 200
    stats = stats_response.json()
    assert stats["window_days"] == 7
    assert stats["total_actions"] >= 1
    assert stats["completed_actions"] >= 1
    assert stats["calls"] >= 1


def test_create_action_log_rejects_invalid_campaign(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=normal_user_token_headers,
        json={
            "campaign_id": str(uuid.uuid4()),
            "action_type": "email",
            "status": "completed",
            "outcome": "sent",
            "confidence_score": 5,
        },
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Campaign not found"


def test_create_action_log_persists_db_row(
    client: TestClient, normal_user_token_headers: dict[str, str], db: Session
) -> None:
    me_response = client.get(
        f"{settings.API_V1_STR}/users/me",
        headers=normal_user_token_headers,
    )
    user_id = uuid.UUID(me_response.json()["id"])
    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=normal_user_token_headers,
    )
    campaign_id = campaigns_response.json()["data"][0]["id"]

    create_response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=normal_user_token_headers,
        json={
            "campaign_id": campaign_id,
            "action_type": "email",
            "status": "completed",
            "outcome": "sent",
            "confidence_score": 3,
        },
    )
    assert create_response.status_code == 200
    action_log_id = create_response.json()["id"]
    action_log = db.get(UserActionLog, action_log_id)
    assert action_log is not None
    assert action_log.user_id == user_id
