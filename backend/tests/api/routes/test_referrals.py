from fastapi.testclient import TestClient

from app.core.config import settings
from tests.utils.utils import random_email


def _signup_and_login(
    client: TestClient, *, email: str, password: str
) -> dict[str, str]:
    signup_response = client.post(
        f"{settings.API_V1_STR}/users/signup",
        json={
            "email": email,
            "password": password,
            "full_name": "Referral User",
        },
    )
    assert signup_response.status_code == 200
    login_response = client.post(
        f"{settings.API_V1_STR}/login/access-token",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_create_referral_link(client: TestClient, normal_user_token_headers: dict[str, str]) -> None:
    response = client.post(
        f"{settings.API_V1_STR}/referrals/link",
        headers=normal_user_token_headers,
        json={"channel": "link"},
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["code"]
    assert payload["channel"] == "link"
    assert payload["invite_url"].startswith(f"{settings.FRONTEND_HOST}/signup?ref=")


def test_referral_claim_and_referrer_metrics(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    link_response = client.post(
        f"{settings.API_V1_STR}/referrals/link",
        headers=normal_user_token_headers,
        json={"channel": "link"},
    )
    assert link_response.status_code == 200
    code = link_response.json()["code"]

    referred_headers = _signup_and_login(
        client,
        email=random_email(),
        password="referralpassword123",
    )
    claim_response = client.post(
        f"{settings.API_V1_STR}/referrals/claim",
        headers=referred_headers,
        json={"code": code},
    )
    assert claim_response.status_code == 200
    assert claim_response.json()["message"] == "Referral claimed"

    referrer_list = client.get(
        f"{settings.API_V1_STR}/referrals/me",
        headers=normal_user_token_headers,
    )
    assert referrer_list.status_code == 200
    payload = referrer_list.json()
    assert payload["count"] >= 1
    assert any(item["code"] == code and item["referred_user_id"] is not None for item in payload["data"])

    assists_response = client.get(
        f"{settings.API_V1_STR}/referrals/me/assists?window=7d",
        headers=normal_user_token_headers,
    )
    assert assists_response.status_code == 200
    assists = assists_response.json()
    assert assists["recruited_users"] >= 1


def test_referral_assists_count_actions_from_referred_users(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    link_response = client.post(
        f"{settings.API_V1_STR}/referrals/link",
        headers=normal_user_token_headers,
        json={"channel": "link"},
    )
    code = link_response.json()["code"]

    referred_headers = _signup_and_login(
        client,
        email=random_email(),
        password="referralpassword456",
    )
    claim_response = client.post(
        f"{settings.API_V1_STR}/referrals/claim",
        headers=referred_headers,
        json={"code": code},
    )
    assert claim_response.status_code == 200

    campaigns_response = client.get(
        f"{settings.API_V1_STR}/campaigns/?status=active",
        headers=referred_headers,
    )
    campaign_id = campaigns_response.json()["data"][0]["id"]

    log_response = client.post(
        f"{settings.API_V1_STR}/actions/log",
        headers=referred_headers,
        json={
            "campaign_id": campaign_id,
            "action_type": "call",
            "status": "completed",
            "outcome": "answered",
            "confidence_score": 4,
        },
    )
    assert log_response.status_code == 200

    assists_response = client.get(
        f"{settings.API_V1_STR}/referrals/me/assists?window=7d",
        headers=normal_user_token_headers,
    )
    assert assists_response.status_code == 200
    payload = assists_response.json()
    assert payload["recruited_users"] >= 1
    assert payload["assisted_actions"] >= 1


def test_referral_claim_rejects_self_claim(
    client: TestClient, normal_user_token_headers: dict[str, str]
) -> None:
    link_response = client.post(
        f"{settings.API_V1_STR}/referrals/link",
        headers=normal_user_token_headers,
        json={"channel": "link"},
    )
    code = link_response.json()["code"]

    response = client.post(
        f"{settings.API_V1_STR}/referrals/claim",
        headers=normal_user_token_headers,
        json={"code": code},
    )
    assert response.status_code == 400
    assert response.json()["detail"] == "You cannot claim your own referral code"
