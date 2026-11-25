import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone

import httpx
import pytest

from handework.extensions import db
from handework.models import EmailQuota, Notification, User
from handework.services import email_delivery as delivery, gmail


@pytest.fixture
def provider(app, monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail_apps_script")
    monkeypatch.setenv("EMAIL_SERVICE_URL", "https://script.google.com/macros/s/test/exec")
    monkeypatch.setenv("EMAIL_SERVICE_SECRET", "fixture-signing-secret")
    db.session.add(EmailQuota(id=1, reserved=0))
    db.session.commit()
    calls = []
    def respond(status=200, result=None, failure=None):
        def post(url, *, json, timeout, follow_redirects):
            calls.append(json)
            assert timeout.connect < timeout.read and not follow_redirects
            if failure:
                raise failure
            return httpx.Response(status, json=result)
        monkeypatch.setattr(gmail.httpx, "post", post)
    respond(result={"ok": True})
    return calls, respond


def queued(customer):
    user = db.session.get(User, customer["user"]["id"])
    row = delivery.queue_email(user, "Payment confirmed", "GHS 10.00")
    db.session.commit()
    return row


def test_signature_redirect_and_delivery_once(provider, customer, monkeypatch):
    calls, _ = provider
    row = queued(customer)
    def redirect(url, **kwargs):
        calls.append(kwargs["json"])
        return httpx.Response(302, headers={"location": "https://script.googleusercontent.com/macros/echo?opaque"})
    monkeypatch.setattr(gmail.httpx, "post", redirect)
    monkeypatch.setattr(gmail.httpx, "get", lambda url, **kw: httpx.Response(200, json={"ok": True}))
    delivery.deliver_email(row.id)
    delivery.deliver_email(row.id)
    assert row.status == "sent" and row.sent_at and len(calls) == 1
    body = calls[0]
    assert set(body) == {"timestamp", "nonce", "payload", "signature"}
    signed = f"{body['timestamp']}.{body['nonce']}.{body['payload']}".encode()
    assert body["signature"] == base64.b64encode(hmac.digest(b"fixture-signing-secret", signed, hashlib.sha256)).decode()
    assert json.loads(body["payload"]) == {"to": customer["user"]["email"], "subject": row.title, "text": row.body}
    assert gmail.send_email("a@example.com", "Unicode", "Café", html="<b>Hi</b>") == "sent"
    assert json.loads(calls[-1]["payload"])["html"] == "<b>Hi</b>"


@pytest.mark.parametrize(("status", "result", "outcome"), [
    (403, {}, "authentication"), (200, {"ok": False, "error": "invalid signature"}, "authentication"),
    (200, {"ok": True, "error": "send failed"}, "rejected"), (200, {"success": False}, "rejected"),
    (200, {"ok": True, "sent": "false"}, "unknown"), (200, {}, "unknown"), (502, {"ok": True}, "unknown"), (200, {"ok": True, "sent": False}, "rejected"),
])
def test_negative_acknowledgements(provider, customer, status, result, outcome):
    calls, respond = provider
    row = queued(customer)
    respond(status, result)
    delivery.deliver_email(row.id)
    delivery.deliver_email(row.id)
    assert len(calls) == 1 and row.status == outcome and not row.sent_at


def test_connection_retry_and_uncertain_read(provider, customer):
    calls, respond = provider
    row = queued(customer)
    respond(failure=httpx.ConnectTimeout("sensitive upstream text"))
    delivery.deliver_email(row.id)
    assert row.status == "queued" and row.next_attempt and not row.sent_at
    delivery.deliver_email(row.id)
    assert len(calls) == 1
    row.next_attempt = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    respond(failure=httpx.ReadTimeout("possibly delivered"))
    delivery.deliver_email(row.id)
    delivery.deliver_email(row.id)
    assert row.status == "unknown" and not row.sent_at and len(calls) == 2
    assert calls[0]["nonce"] != calls[1]["nonce"]


@pytest.mark.parametrize("provider_quota", [True, False])
def test_shared_daily_budget(provider, customer, monkeypatch, provider_quota):
    calls, respond = provider
    monkeypatch.setenv("EMAIL_DAILY_RECIPIENT_LIMIT", "1")
    first, second = queued(customer), queued(customer)
    if provider_quota:
        respond(200, {"ok": False, "error": "Daily recipient quota exhausted"})
    delivery.deliver_email(first.id)
    delivery.deliver_email(second.id)
    assert len(calls) == 1
    assert bool(first.sent_at) != provider_quota
    assert second.status == "queued" and not second.sent_at
    assert delivery.utc(second.next_attempt) > datetime.now(timezone.utc) + timedelta(hours=23)


def test_account_email_and_password_recovery(provider, customer, client, caplog):
    calls, _ = provider
    caplog.set_level(logging.INFO)
    user = db.session.get(User, customer["user"]["id"])
    def consume(action, password=None):
        row = Notification.query.filter_by(title=delivery.ACCOUNT_SUBJECTS[action], user_id=user.id).one()
        delivery.deliver_email(row.id)
        text = json.loads(calls[-1]["payload"])["text"]
        code = delivery.account_code(row, user)
        assert code in text and code not in row.body and code not in str(row.data)
        assert code not in caplog.text and "fixture-signing-secret" not in caplog.text
        data = {"code": code, "email": user.email, "password": password}
        path = f"/v1/auth/email/{action}/confirm"
        assert client.post(path, json={**data, "code": "wrong"}).status_code == 422
        assert client.post(path, json=data).status_code == 200
        assert client.post(path, json=data).status_code == 422
    consume("verify")
    assert user.email_verified_at
    for email in (user.email, "missing@example.com", user.email):
        assert client.post("/v1/auth/email/reset/request", json={"email": email}).status_code == 202
    consume("reset", "NewPass12345")
    assert client.get("/v1/auth/me", headers=customer["headers"]).status_code == 401
    assert client.post("/v1/auth/login", json={"email": user.email, "password": "NewPass12345"}).status_code == 200


def test_expired_account_code_skips_provider(provider, customer):
    calls, _ = provider
    row = Notification.query.filter_by(title=delivery.ACCOUNT_SUBJECTS["verify"]).one()
    row.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
    db.session.commit()
    delivery.deliver_email(row.id)
    assert not calls and row.status == "expired"


def test_marketplace_email_events(provider, client, customer, artisan, monkeypatch):
    from handework.models import Role
    from test_payment_lifecycle import funded

    booking_id, _ = funded(client, customer, artisan, monkeypatch)
    dispute = client.post("/v1/disputes", headers=customer["headers"],
                          json={"booking_id": booking_id, "reason": "quality", "description": "Review requested"}).json
    verification = client.post("/v1/artisans/me/verifications", headers=artisan["headers"],
                               data={"kind": "payout_name", "value": "Kojo Test"}).json
    db.session.get(User, customer["user"]["id"]).role = Role.ADMIN
    db.session.commit()
    assert client.post(f"/v1/admin/disputes/{dispute['id']}/decision", headers=customer["headers"],
                       json={"decision": "no_action"}).status_code == 200
    for _ in range(2):
        assert client.post(f"/v1/admin/verifications/{verification['id']}/decision", headers=customer["headers"],
                           json={"decision": "approved"}).status_code == 200

    for account, titles in [(customer, ["Booking created", "New artisan quote", "Dispute opened", "Dispute resolved"]),
                            (artisan, ["Quotation requested", "Quote accepted", "Dispute opened", "Dispute resolved",
                                       "Verification submitted", "Verification updated"])]:
        for title in titles:
            assert Notification.query.filter_by(channel="email", title=title, user_id=account["user"]["id"]).count() == 1


def test_worker_recovers_queued_rows_after_restart(provider, customer, monkeypatch):
    from handework.tasks import deliver_notification, drain_email
    calls, _ = provider
    waiting, uncertain = queued(customer), queued(customer)
    uncertain.status = "sending"
    uncertain.next_attempt = datetime.now(timezone.utc) - timedelta(minutes=1)
    db.session.commit()
    monkeypatch.setattr(deliver_notification, "delay", deliver_notification.run)
    drain_email.run()
    drain_email.run()
    assert waiting.status == "sent" and uncertain.status == "unknown"
    # Registration also created a verification email.
    assert len(calls) == 2


def test_explicit_unsent_failure_is_retried(provider, customer):
    calls, respond = provider
    row = queued(customer)
    respond(503, {"ok": False, "sent": False, "retryable": True})
    delivery.deliver_email(row.id)
    assert row.status == "queued" and not row.sent_at
    row.next_attempt = datetime.now(timezone.utc) - timedelta(seconds=1)
    db.session.commit()
    respond(200, {"success": True})
    delivery.deliver_email(row.id)
    assert len(calls) == 2 and row.sent_at and row.status == "sent"
