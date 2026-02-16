import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session

from app.core.config import settings
from app.models import (
    ActionTemplate,
    ActionType,
    Campaign,
    CampaignCreate,
    CampaignStatus,
    OfficeType,
    RepresentativeTarget,
)


def test_read_campaigns_returns_seeded_data(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert len(payload["data"]) >= 1
    first = payload["data"][0]
    assert "id" in first
    assert "slug" in first
    assert "title" in first
    assert first["status"] in {status.value for status in CampaignStatus}


def test_read_campaigns_supports_status_filter(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"paused-{uuid.uuid4().hex[:8]}",
            title="Paused Campaign",
            description="Used in tests",
            policy_topic="test",
            status=CampaignStatus.PAUSED,
        )
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    response = client.get(
        f"{settings.API_V1_STR}/campaigns/?status={CampaignStatus.ACTIVE.value}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert all(
        campaign_row["status"] == CampaignStatus.ACTIVE.value
        for campaign_row in payload["data"]
    )
    assert all(campaign_row["id"] != str(campaign.id) for campaign_row in payload["data"])


def test_read_campaign_by_id(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    all_campaigns = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=superuser_token_headers,
    )
    campaign_id = all_campaigns.json()["data"][0]["id"]
    response = client.get(
        f"{settings.API_V1_STR}/campaigns/{campaign_id}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == campaign_id
    assert "slug" in payload
    assert "description" in payload


def test_read_campaign_by_id_not_found(
    client: TestClient, superuser_token_headers: dict[str, str]
) -> None:
    response = client.get(
        f"{settings.API_V1_STR}/campaigns/{uuid.uuid4()}",
        headers=superuser_token_headers,
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Campaign not found"


def test_read_campaign_targets(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"targets-{uuid.uuid4().hex[:8]}",
            title="Target Campaign",
            description="Campaign with target for testing",
            policy_topic="test",
            status=CampaignStatus.ACTIVE,
        )
    )
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    target = RepresentativeTarget(
        campaign_id=campaign.id,
        office_type=OfficeType.SENATE,
        office_name="Test Senate Office",
        state_code="TX",
    )
    db.add(target)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/campaigns/{campaign.id}/targets",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert len(payload["data"]) >= 1
    assert payload["data"][0]["campaign_id"] == str(campaign.id)


def test_read_campaign_templates(
    client: TestClient, superuser_token_headers: dict[str, str], db: Session
) -> None:
    campaign = Campaign.model_validate(
        CampaignCreate(
            slug=f"templates-{uuid.uuid4().hex[:8]}",
            title="Template Campaign",
            description="Campaign with template for testing",
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
        title="Call Template",
        script_text="Please support this campaign",
    )
    db.add(template)
    db.commit()

    response = client.get(
        f"{settings.API_V1_STR}/campaigns/{campaign.id}/templates",
        headers=superuser_token_headers,
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["count"] >= 1
    assert len(payload["data"]) >= 1
    assert payload["data"][0]["campaign_id"] == str(campaign.id)
