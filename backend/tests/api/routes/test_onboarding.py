import uuid

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app.core.config import settings
from app.models import DailyActionPlan, UserPrivacySettings, UserProfile


def test_complete_onboarding_creates_profile_privacy_and_daily_plan(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=normal_user_token_headers,
    )
    assert campaigns_response.status_code == 200
    campaign_id = campaigns_response.json()["data"][0]["id"]

    payload = {
        "username": f"user_{uuid.uuid4().hex[:10]}",
        "state_code": "TX",
        "district_code": "01",
        "timezone": "America/Chicago",
        "visibility_mode": "private",
        "campaign_ids": [campaign_id],
        "target_actions_per_day": 3,
        "active_weekdays_mask": "1111100",
    }
    response = client.post(
        f"{settings.API_V1_STR}/onboarding/complete",
        headers=normal_user_token_headers,
        json=payload,
    )
    assert response.status_code == 200
    content = response.json()
    assert content["profile"]["username"] == payload["username"]
    assert content["privacy"]["show_on_leaderboard"] is False
    assert content["daily_plans_count"] >= 1

    profile_response = client.get(
        f"{settings.API_V1_STR}/profile/me",
        headers=normal_user_token_headers,
    )
    assert profile_response.status_code == 200
    assert profile_response.json()["username"] == payload["username"]

    privacy_response = client.get(
        f"{settings.API_V1_STR}/privacy/me",
        headers=normal_user_token_headers,
    )
    assert privacy_response.status_code == 200
    assert privacy_response.json()["show_on_leaderboard"] is False


def test_complete_onboarding_rejects_duplicate_username(
    client: TestClient,
    normal_user_token_headers: dict[str, str],
    superuser_token_headers: dict[str, str],
) -> None:
    username = f"user_{uuid.uuid4().hex[:10]}"
    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/",
        headers=normal_user_token_headers,
    )
    campaign_id = campaigns_response.json()["data"][0]["id"]

    first_payload = {
        "username": username,
        "state_code": "TX",
        "timezone": "America/Chicago",
        "visibility_mode": "private",
        "campaign_ids": [campaign_id],
        "target_actions_per_day": 2,
        "active_weekdays_mask": "1111100",
    }
    first_response = client.post(
        f"{settings.API_V1_STR}/onboarding/complete",
        headers=normal_user_token_headers,
        json=first_payload,
    )
    assert first_response.status_code == 200

    second_payload = {
        "username": username,
        "state_code": "CA",
        "timezone": "America/Los_Angeles",
        "visibility_mode": "community",
        "campaign_ids": [campaign_id],
        "target_actions_per_day": 2,
        "active_weekdays_mask": "1111100",
    }
    second_response = client.post(
        f"{settings.API_V1_STR}/onboarding/complete",
        headers=superuser_token_headers,
        json=second_payload,
    )
    assert second_response.status_code == 409
    assert second_response.json()["detail"] == "Username is already taken"


def test_onboarding_persists_records(client: TestClient, db: Session) -> None:
    username = f"persist_{uuid.uuid4().hex[:10]}"
    signup_data = {
        "email": f"{uuid.uuid4().hex[:8]}@example.com",
        "password": "verysecurepassword",
        "full_name": "Persist User",
    }
    signup_response = client.post(f"{settings.API_V1_STR}/users/signup", json=signup_data)
    assert signup_response.status_code == 200

    login_data = {
        "username": signup_data["email"],
        "password": signup_data["password"],
    }
    login_response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data=login_data,
    )
    token = login_response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    campaigns_response = client.get(f"{settings.API_V1_STR}/campaigns/", headers=headers)
    campaign_id = campaigns_response.json()["data"][0]["id"]

    response = client.post(
        f"{settings.API_V1_STR}/onboarding/complete",
        headers=headers,
        json={
            "username": username,
            "timezone": "America/Chicago",
            "visibility_mode": "private",
            "campaign_ids": [campaign_id],
            "target_actions_per_day": 3,
            "active_weekdays_mask": "1111100",
        },
    )
    assert response.status_code == 200
    user_id = uuid.UUID(signup_response.json()["id"])

    profile = db.exec(select(UserProfile).where(UserProfile.user_id == user_id)).first()
    assert profile is not None
    assert profile.username == username

    privacy = db.exec(
        select(UserPrivacySettings).where(UserPrivacySettings.user_id == user_id)
    ).first()
    assert privacy is not None

    plan = db.exec(
        select(DailyActionPlan).where(DailyActionPlan.user_id == user_id)
    ).first()
    assert plan is not None
