import time

import pyotp
import pytest

from cryptography.fernet import Fernet
from handework.extensions import db
from handework.models import UserTotp, UserTotpRecoveryCode
from handework.services import totp


@pytest.fixture
def authenticator(monkeypatch):
    monkeypatch.setenv("TOTP_ENABLED", "true")
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "false")
    monkeypatch.setenv("TOTP_ISSUER", "handEwork")
    monkeypatch.setenv(
        "TOTP_ENCRYPTION_KEY",
        Fernet.generate_key().decode()
    )

    clock = [int(time.time()) // 30 * 30]

    original = totp.matching_step

    def controlled_step(secret, code, last_used_step=None, now=None):
        return original(
            secret, code, last_used_step, now=clock[0]
        )

    monkeypatch.setattr(totp, "matching_step", controlled_step)
    monkeypatch.setattr(
        "handework.routes.authenticator.matching_step",
        controlled_step
    )

    return clock


def login(client, code=None):
    data = {
        "email": "ama@example.com",
        "password": "StrongPass123"
    }

    if code is not None:
        data["totp_code"] = code

    return client.post("/v1/auth/login", json=data)


def enroll(client, customer, clock):
    response = client.post(
        "/v1/auth/totp/setup",
        headers=customer["headers"],
        json={"password": "StrongPass123"}
    )

    assert response.status_code == 200

    body = response.get_json()
    secret = body["secret"]

    assert body["qr_code"].startswith(
        "data:image/png;base64,"
    )

    assert "no-store" in {part.strip().lower() for part in response.headers["Cache-Control"].split(",")}

    response = client.post(
        "/v1/auth/totp/enable",
        headers=customer["headers"],
        json={"code": pyotp.TOTP(secret).at(clock[0])}
    )

    assert response.status_code == 200

    codes = response.get_json()["recovery_codes"]
    assert len(codes) == 10

    clock[0] += 60

    return secret, codes


def test_setup_requires_authentication(client, authenticator):
    response = client.post(
        "/v1/auth/totp/setup",
        json={"password": "StrongPass123"}
    )

    assert response.status_code == 401


def test_setup_requires_correct_password(
    client, customer, authenticator
):
    response = client.post(
        "/v1/auth/totp/setup",
        headers=customer["headers"],
        json={"password": "incorrect"}
    )

    assert response.status_code == 403


def test_password_only_login_blocked(
    client, customer, authenticator
):
    enroll(client, customer, authenticator)

    response = login(client)

    assert response.status_code == 401
    assert response.get_json()["code"] == "totp_required"
    assert "access_token" not in response.get_json()
    assert "refresh_token" not in response.get_json()


def test_valid_authenticator_login(
    client, customer, authenticator
):
    secret, _ = enroll(client, customer, authenticator)

    response = login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    )

    assert response.status_code == 200
    assert response.get_json()["access_token"]
    assert response.get_json()["refresh_token"]


def test_authenticator_replay_blocked(
    client, customer, authenticator
):
    secret, _ = enroll(client, customer, authenticator)

    code = pyotp.TOTP(secret).at(authenticator[0])

    assert login(client, code).status_code == 200
    assert login(client, code).status_code == 401


def test_recovery_code_single_use(
    client, customer, authenticator
):
    _, codes = enroll(client, customer, authenticator)

    assert login(client, codes[0]).status_code == 200
    assert login(client, codes[0]).status_code == 401
    assert login(client, codes[1]).status_code == 200


def test_existing_sessions_revoked(
    client, customer, authenticator
):
    enroll(client, customer, authenticator)

    response = client.get(
        "/v1/auth/me",
        headers=customer["headers"]
    )

    assert response.status_code == 401


def test_secrets_not_stored_in_plaintext(
    client, customer, authenticator
):
    secret, codes = enroll(
        client, customer, authenticator
    )

    user_id = customer["user"]["id"]

    row = db.session.get(UserTotp, user_id)

    assert row.secret_encrypted != secret
    assert row.pending_secret_encrypted is None

    records = UserTotpRecoveryCode.query.filter_by(
        user_id=user_id
    ).all()

    assert len(records) == 10

    for record in records:
        assert record.code_hash not in codes


def test_disabled_enrollment_cannot_bypass_2fa(
    client, customer, authenticator, monkeypatch
):
    secret, _ = enroll(
        client, customer, authenticator
    )

    monkeypatch.setenv("TOTP_ENABLED", "false")

    assert login(client).status_code == 401

    response = login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    )

    assert response.status_code == 200


def test_five_failed_attempts_lock_authenticator(
    client, customer, authenticator
):
    secret, _ = enroll(client, customer, authenticator)

    generator = pyotp.TOTP(secret)

    valid = {
        generator.at(authenticator[0] + offset)
        for offset in (-30, 0, 30)
    }

    wrong = next(
        f"{n:06d}" for n in range(1000000)
        if f"{n:06d}" not in valid
    )

    for _ in range(5):
        assert login(client, wrong).status_code == 401

    response = login(
        client,
        generator.at(authenticator[0])
    )

    assert response.status_code == 429
    assert response.get_json()["code"] == "totp_locked"

def authenticated_headers(response):
    assert response.status_code == 200

    return {
        "Authorization":
            "Bearer " + response.get_json()["access_token"]
    }


def test_disable_requires_second_factor(
    client, customer, authenticator
):
    secret, _ = enroll(client, customer, authenticator)

    headers = authenticated_headers(login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    ))

    response = client.post(
        "/v1/auth/totp/disable",
        headers=headers,
        json={"password": "StrongPass123"}
    )

    assert response.status_code == 422
    assert login(client).status_code == 401


def test_disable_authenticator(
    client, customer, authenticator
):
    secret, _ = enroll(client, customer, authenticator)

    headers = authenticated_headers(login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    ))

    authenticator[0] += 60

    response = client.post(
        "/v1/auth/totp/disable",
        headers=headers,
        json={
            "password": "StrongPass123",
            "code": pyotp.TOTP(secret).at(authenticator[0])
        }
    )

    assert response.status_code == 200
    assert not response.get_json()["enabled"]

    assert client.get(
        "/v1/auth/me", headers=headers
    ).status_code == 401

    assert login(client).status_code == 200

    assert db.session.get(
        UserTotp, customer["user"]["id"]
    ) is None


def test_regenerate_recovery_codes(
    client, customer, authenticator
):
    secret, previous_codes = enroll(
        client, customer, authenticator
    )

    headers = authenticated_headers(login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    ))

    authenticator[0] += 60

    response = client.post(
        "/v1/auth/totp/recovery/regenerate",
        headers=headers,
        json={
            "password": "StrongPass123",
            "code": pyotp.TOTP(secret).at(authenticator[0])
        }
    )

    assert response.status_code == 200

    new_codes = response.get_json()["recovery_codes"]

    assert len(new_codes) == 10
    assert not set(new_codes).intersection(previous_codes)

    assert login(client, previous_codes[0]).status_code == 401
    assert login(client, new_codes[0]).status_code == 200

    assert client.get(
        "/v1/auth/me", headers=headers
    ).status_code == 401

@pytest.fixture
def administrator(client, customer):
    from handework.models import User, Role

    user = db.session.get(
        User, customer["user"]["id"]
    )

    user.role = Role.ADMIN
    user.session_version += 1

    db.session.commit()

    response = login(client)

    assert response.status_code == 200

    body = response.get_json()

    return {
        "headers": {
            "Authorization": "Bearer " + body["access_token"]
        },
        "refresh_token": body["refresh_token"],
        "user": body["user"]
    }


def test_admin_enforcement_blocks_unenrolled_account(
    client, administrator, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    response = client.get(
        "/v1/admin/queue",
        headers=administrator["headers"]
    )

    assert response.status_code == 403
    assert response.get_json()["code"] == (
        "admin_totp_enrollment_required"
    )


def test_admin_can_access_security_settings(
    client, administrator, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    response = client.get(
        "/v1/auth/totp/status",
        headers=administrator["headers"]
    )

    assert response.status_code == 200
    assert response.get_json()["required"] is True
    assert response.get_json()["enabled"] is False

    response = client.get(
        "/v1/auth/me",
        headers=administrator["headers"]
    )

    assert response.status_code == 200


def test_enrolled_admin_can_access_operations(
    client, administrator, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    secret, _ = enroll(
        client, administrator, authenticator
    )

    response = login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    )

    headers = authenticated_headers(response)

    response = client.get(
        "/v1/admin/queue",
        headers=headers
    )

    assert response.status_code == 200


def test_admin_cannot_disable_required_authenticator(
    client, administrator, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    secret, _ = enroll(
        client, administrator, authenticator
    )

    headers = authenticated_headers(login(
        client,
        pyotp.TOTP(secret).at(authenticator[0])
    ))

    authenticator[0] += 60

    response = client.post(
        "/v1/auth/totp/disable",
        headers=headers,
        json={
            "password": "StrongPass123",
            "code": pyotp.TOTP(secret).at(authenticator[0])
        }
    )

    assert response.status_code == 403

    row = db.session.get(
        UserTotp, administrator["user"]["id"]
    )

    assert row.enabled_at is not None


def test_admin_old_refresh_token_revoked(
    client, administrator, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    enroll(client, administrator, authenticator)

    response = client.post(
        "/v1/auth/refresh",
        headers={
            "Authorization":
                "Bearer " + administrator["refresh_token"]
        }
    )

    assert response.status_code == 401
    assert "access_token" not in response.get_json()


def test_customer_totp_remains_optional(
    client, customer, authenticator, monkeypatch
):
    monkeypatch.setenv("TOTP_ADMIN_REQUIRED", "true")

    response = login(client)

    assert response.status_code == 200
    assert response.get_json()["access_token"]

    response = client.get(
        "/v1/auth/totp/status",
        headers=customer["headers"]
    )

    assert response.status_code == 200
    assert response.get_json()["required"] is False
