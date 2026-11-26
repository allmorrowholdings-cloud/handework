"""Google identity mapping and authorization regression tests; no Google network requests."""
from handework.extensions import db
from handework.models import GoogleIdentity

CLAIMS = {"iss": "https://accounts.google.com", "sub": "google-unique-user-123", "email": "new-person@gmail.com", "email_verified": True, "given_name": "New", "family_name": "Person"}


def test_google_login_rejects_missing_configuration(client):
    response = client.post('/v1/auth/google/login', json={'credential': 'untrusted'})
    assert response.status_code == 401


def test_google_signup_and_signin(client, app, monkeypatch):
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: CLAIMS)
    payload = {'credential': 'stub', 'first_name': 'New', 'last_name': 'Person', 'phone': '0244000021', 'password': 'StrongPassphraseForGoogle123', 'client': 'web'}
    response = client.post('/v1/auth/google/register', json=payload)
    assert response.status_code == 201
    user_id = response.get_json()['user']['id']
    with app.app_context():
        assert GoogleIdentity.query.filter_by(google_sub=CLAIMS['sub']).one().user_id == user_id
    signed = client.post('/v1/auth/google/login', json={'credential': 'stub', 'client': 'web'})
    assert signed.status_code == 200
    assert signed.get_json()['user']['id'] == user_id


def test_google_cannot_auto_link_existing_password_account(client, customer, monkeypatch):
    claims = {**CLAIMS, 'email': customer['user']['email']}
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: claims)
    attempt = client.post('/v1/auth/google/login', json={'credential': 'stub', 'client': 'web'})
    assert attempt.status_code == 409
    assert attempt.get_json()['code'] == 'google_link_required'


def test_explicit_google_link_requires_account_password(client, customer, monkeypatch):
    claims = {**CLAIMS, 'email': customer['user']['email']}
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: claims)
    endpoint = '/v1/auth/google/link'
    response = client.post(endpoint, json={'credential': 'stub', 'password': 'wrong'}, headers=customer['headers'])
    assert response.status_code == 403
    linked = client.post(endpoint, json={'credential': 'stub', 'password': 'StrongPass123'}, headers=customer['headers'])
    assert linked.status_code == 200
    login = client.post('/v1/auth/google/login', json={'credential': 'stub', 'client': 'web'})
    assert login.status_code == 200
    assert login.get_json()['user']['id'] == customer['user']['id']


def test_google_progressive_registration_profile(client, monkeypatch):
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: CLAIMS)
    response = client.post('/v1/auth/google/login', json={'credential': 'stub', 'client': 'web'})
    assert response.status_code == 404
    assert response.get_json()['code'] == 'google_registration_required'
    assert response.get_json()['profile']['first_name'] == 'New'
    assert response.get_json()['profile']['email'] == CLAIMS['email']


def test_google_inline_link_needs_password_and_avoids_duplicates(client, customer, monkeypatch):
    claims = {**CLAIMS, 'email': customer['user']['email']}
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: claims)
    url = '/v1/auth/google/verify-and-link'
    bad = client.post(url, json={'credential': 'stub', 'password': 'bad', 'client': 'web'})
    assert bad.status_code == 401
    success = client.post(url, json={'credential': 'stub', 'password': 'StrongPass123', 'client': 'web'})
    assert success.status_code == 200
    assert success.get_json()['user']['id'] == customer['user']['id']
    again = client.post(url, json={'credential': 'stub', 'password': 'StrongPass123', 'client': 'web'})
    assert again.status_code == 409


def test_google_inline_link_keeps_mfa(client, customer, monkeypatch):
    from datetime import datetime, timezone
    from handework.models import UserTotp
    from handework.extensions import db
    claims = {**CLAIMS, 'email': customer['user']['email']}
    monkeypatch.setattr('handework.routes.google_auth.verified_identity', lambda _: claims)
    with client.application.app_context():
        db.session.add(UserTotp(user_id=customer['user']['id'], enabled_at=datetime.now(timezone.utc)))
        db.session.commit()
    response = client.post('/v1/auth/google/verify-and-link', json={
        'credential': 'stub', 'password': 'StrongPass123', 'client': 'web'
    })
    assert response.status_code == 401
    assert response.get_json()['code'] == 'totp_required'
