from datetime import datetime, timedelta, timezone
from handework.extensions import db
from handework.models import LoginSession


def login(client):
    response = client.post("/v1/auth/login", json={
        "email": "ama@example.com", "password": "StrongPass123", "client": "web",
    })
    assert response.status_code == 200
    return response.get_json()


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_logout_revokes_only_this_browser(client, customer):
    browser = login(client)
    other_device = login(client)
    renewed = client.post("/v1/auth/refresh", headers=bearer(browser["refresh_token"])).get_json()
    assert client.post("/v1/auth/logout", headers=bearer(renewed["refresh_token"])).status_code == 204
    assert client.get("/v1/auth/me", headers=bearer(browser["access_token"])).status_code == 401
    assert client.post("/v1/auth/refresh", headers=bearer(browser["refresh_token"])).status_code == 401
    assert client.get("/v1/auth/me", headers=bearer(other_device["access_token"])).status_code == 200


def test_idle_browser_must_sign_in_again(client, customer):
    browser = login(client)
    session = LoginSession.query.one()
    session.last_active = datetime.now(timezone.utc) - timedelta(hours=24, seconds=1)
    db.session.commit()
    assert client.get("/v1/auth/me", headers=bearer(browser["access_token"])).status_code == 401
    assert client.post("/v1/auth/refresh", headers=bearer(browser["refresh_token"])).status_code == 401


def test_catalog_includes_new_trade(client, artisan):
    assert "Plumber" in client.get("/v1/services").get_json()["items"]


def test_sign_in_preserves_provisioned_role(client, customer, monkeypatch):
    monkeypatch.setenv("ADMIN_EMAILS", "ama@example.com")
    assert login(client)["user"]["role"] == "customer"
