import re

import pytest

from handework.services import phone_verification as otp

@pytest.fixture
def verification(monkeypatch):
    monkeypatch.setenv(
        "REDIS_URL", "redis://127.0.0.1:6381/15"
    )
    monkeypatch.setenv("SMS_ENABLED", "true")
    monkeypatch.setenv("PHONE_OTP_ENABLED", "true")
    monkeypatch.setenv(
        "SECRET_KEY",
        "local-testing-secret-not-for-production-123456"
    )

    messages = []

    def fake_sms(phone, message):
        messages.append((phone, message))
        return {"status": "success"}

    monkeypatch.setattr(otp, "send_sms", fake_sms)

    original_connection = otp.connection

    def cleanup():
        with original_connection() as client:
            keys = list(client.scan_iter("handework:otp:*"))
            if keys:
                client.delete(*keys)

    cleanup()
    try:
        yield messages
    finally:
        cleanup()

def get_code(messages):
    return re.search(
        r"\b[0-9]{6}\b", messages[-1][1]
    ).group()

def test_otp_requires_authentication(client, verification):
    assert client.post(
        "/v1/auth/phone/request"
    ).status_code == 401

    assert client.post(
        "/v1/auth/phone/confirm",
        json={"code": "123456"}
    ).status_code == 401

    assert not verification

def test_customer_phone_verification(
    client, customer, verification
):
    headers = customer["headers"]

    response = client.post(
        "/v1/auth/phone/request",
        headers=headers
    )
    assert response.status_code == 202
    assert len(verification) == 1

    response = client.post(
        "/v1/auth/phone/request",
        headers=headers
    )
    assert response.status_code == 429
    assert len(verification) == 1

    code = get_code(verification)
    wrong = "000000" if code != "000000" else "111111"

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=headers,
        json={"code": wrong}
    )
    assert response.status_code == 422

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=headers,
        json={"code": code}
    )
    assert response.status_code == 200
    assert response.get_json()["user"]["phone_verified"]

    response = client.get(
        "/v1/auth/me",
        headers=headers
    )
    assert response.get_json()["user"]["phone_verified"]

    response = client.post(
        "/v1/auth/phone/request",
        headers=headers
    )
    assert response.status_code == 200
    assert len(verification) == 1

def test_artisan_phone_verification(
    client, artisan, verification
):
    headers = artisan["headers"]

    assert client.post(
        "/v1/auth/phone/request",
        headers=headers
    ).status_code == 202

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=headers,
        json={"code": get_code(verification)}
    )

    assert response.status_code == 200
    assert response.get_json()["user"]["phone_verified"]
    assert response.get_json()["user"]["role"] == "artisan"

def test_phone_change_resets_verification(
    client, customer, verification
):
    headers = customer["headers"]

    assert client.post(
        "/v1/auth/phone/request",
        headers=headers
    ).status_code == 202

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=headers,
        json={"code": get_code(verification)}
    )
    assert response.get_json()["user"]["phone_verified"]

    response = client.patch(
        "/v1/auth/me",
        headers=headers,
        json={"phone": "0244000099"}
    )

    assert response.status_code == 200
    assert not response.get_json()["user"]["phone_verified"]

def test_phone_change_invalidates_pending_code(
    client, customer, verification
):
    headers = customer["headers"]

    assert client.post(
        "/v1/auth/phone/request",
        headers=headers
    ).status_code == 202

    code = get_code(verification)

    assert client.patch(
        "/v1/auth/me",
        headers=headers,
        json={"phone": "0244000099"}
    ).status_code == 200

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=headers,
        json={"code": code}
    )
    assert response.status_code == 422

def test_disabled_phone_verification(
    client, customer, verification, monkeypatch
):
    monkeypatch.setenv("PHONE_OTP_ENABLED", "false")

    response = client.post(
        "/v1/auth/phone/request",
        headers=customer["headers"]
    )

    assert response.status_code == 503
    assert not verification

def test_redis_failure_blocks_verification(
    client, customer, verification, monkeypatch
):
    def unavailable():
        raise ConnectionError("Test Redis failure")

    monkeypatch.setattr(otp, "connection", unavailable)

    response = client.post(
        "/v1/auth/phone/request",
        headers=customer["headers"]
    )

    assert response.status_code == 503
    assert not verification

def test_cross_account_otp_rejected(
    client, customer, artisan, verification
):
    assert client.post(
        "/v1/auth/phone/request",
        headers=customer["headers"]
    ).status_code == 202

    response = client.post(
        "/v1/auth/phone/confirm",
        headers=artisan["headers"],
        json={"code": get_code(verification)}
    )

    assert response.status_code == 422

