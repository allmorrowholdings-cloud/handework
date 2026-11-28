"""Regression tests for Batch 04 session authorization and response hardening."""
from datetime import datetime, timedelta, timezone

from handework.extensions import db
from handework.models import LoginSession, User


def bearer(token):
    return {"Authorization": f"Bearer {token}"}


def test_deactivated_account_tokens_are_invalid(client, customer):
    token = customer['headers']['Authorization'].removeprefix('Bearer ')
    assert client.get('/v1/auth/me', headers=bearer(token)).status_code == 200
    user = User.query.filter_by(email='ama@example.com').first()
    user.status = 'suspended'
    db.session.commit()
    assert client.get('/v1/auth/me', headers=bearer(token)).status_code == 401


def test_installed_refresh_token_retains_30_day_idle_policy(client, customer):
    response = client.post('/v1/auth/login', json={
        'email':'ama@example.com', 'password':'StrongPass123', 'client':'installed',
    })
    assert response.status_code == 200
    body = response.get_json()
    session = LoginSession.query.one()
    session.last_active = datetime.now(timezone.utc) - timedelta(days=2)
    db.session.commit()
    assert client.post('/v1/auth/refresh', headers=bearer(body['refresh_token'])).status_code == 200


def test_installed_refresh_token_expires_after_30_days_idle(client, customer):
    response = client.post('/v1/auth/login', json={
        'email':'ama@example.com', 'password':'StrongPass123', 'client':'installed',
    })
    assert response.status_code == 200
    body = response.get_json()
    session = LoginSession.query.one()
    session.last_active = datetime.now(timezone.utc) - timedelta(days=30, minutes=2)
    db.session.commit()
    assert client.post('/v1/auth/refresh', headers=bearer(body['refresh_token'])).status_code == 401


def test_security_response_headers(client):
    response = client.get('/v1/health')
    assert response.headers['X-Content-Type-Options']=='nosniff'
    assert response.headers['X-Frame-Options']=='DENY'
    assert 'camera=()' in response.headers['Permissions-Policy']
    assert response.headers['Cache-Control']=='private, no-store'
    assert response.headers['Pragma']=='no-cache'


def test_phone_confirm_rejects_non_object_json(client, customer, monkeypatch):
    monkeypatch.setenv('PHONE_OTP_ENABLED','true')
    monkeypatch.setenv('SMS_ENABLED','true')
    result = client.post('/v1/auth/phone/confirm', headers=customer['headers'], json=['123456'])
    assert result.status_code == 422
