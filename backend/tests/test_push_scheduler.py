import pytest

from handework.services import firebase_push


def test_scheduler_rejects_unauthorized_requests(client, monkeypatch):
    monkeypatch.setenv(
        "NOTIFICATION_SCHEDULER_TOKEN", "x" * 64
    )

    response = client.post(
        "/v1/internal/notifications/tick"
    )

    assert response.status_code == 403


def test_scheduler_disabled(client, monkeypatch):
    monkeypatch.setenv(
        "NOTIFICATION_SCHEDULER_TOKEN", "x" * 64
    )

    monkeypatch.setenv(
        "NOTIFICATION_SCHEDULER_ENABLED", "false"
    )

    response = client.post(
        "/v1/internal/notifications/tick",
        headers={"Authorization": "Bearer " + "x" * 64}
    )

    assert response.status_code == 200
    assert response.json["processed"] == 0
    assert response.json["enabled"] is False


def test_browser_registration_requires_login(client):
    response = client.post(
        "/v1/push-devices/browser",
        json={"token": "x" * 100}
    )

    assert response.status_code == 401


def test_browser_registration_and_removal(
    client, customer, monkeypatch
):
    from handework.models import PushDevice

    monkeypatch.setenv("FIREBASE_PUSH_ENABLED", "true")

    token = "test-browser-token-" + "x" * 100

    response = client.post(
        "/v1/push-devices/browser",
        headers=customer["headers"],
        json={"token": token}
    )

    assert response.status_code == 201

    row = PushDevice.query.filter_by(
        expo_push_token=token
    ).one()

    assert row.active
    assert row.platform == "web"
    assert row.user_id == customer["user"]["id"]

    response = client.post(
        "/v1/push-devices/browser/remove",
        headers=customer["headers"],
        json={"token": token}
    )

    assert response.status_code == 200

    row = PushDevice.query.filter_by(
        expo_push_token=token
    ).one()

    assert row.active is False


def test_disabled_firebase_never_sends(monkeypatch):
    monkeypatch.setenv("FIREBASE_PUSH_ENABLED", "false")

    def deny(*args, **kwargs):
        raise AssertionError("Unexpected Firebase request")

    monkeypatch.setattr(
        firebase_push.messaging, "send", deny
    )

    assert firebase_push.send_web_push("test") == "disabled"


def test_firebase_send_mocked(monkeypatch):
    monkeypatch.setenv("FIREBASE_PUSH_ENABLED", "true")

    monkeypatch.setattr(
        firebase_push, "firebase_app", lambda: None
    )

    def fake_send(message, app=None):
        assert message.token == "test-token"
        assert message.notification.title == "handEwork"
        return "mock-message-id"

    monkeypatch.setattr(
        firebase_push.messaging, "send", fake_send
    )

    assert firebase_push.send_web_push(
        "test-token"
    ) == "accepted"
