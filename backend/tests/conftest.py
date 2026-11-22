import pytest
from handework import create_app
from handework.config import TestConfig
from handework.extensions import db


@pytest.fixture()
def app():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture()
def client(app): return app.test_client()


@pytest.fixture()
def customer(client):
    response=client.post("/v1/auth/register",json={"first_name":"Ama","last_name":"Test","email":"ama@example.com","phone":"0244000001","password":"StrongPass123"})
    body=response.get_json();return {"headers":{"Authorization":f"Bearer {body['access_token']}"},"user":body["user"]}


@pytest.fixture()
def artisan(client,app):
    response=client.post("/v1/auth/register-artisan",json={"first_name":"Kojo","last_name":"Test","email":"kojo@example.com","phone":"0244000002","password":"StrongPass123","trade":"Plumber","city":"Accra","area":"Osu","years_experience":5,"radius_km":25})
    body=response.get_json()
    from handework.models import ArtisanProfile
    with app.app_context():
        profile=ArtisanProfile.query.filter_by(user_id=body["user"]["id"]).first();profile.verification_status="approved";profile.available=True;profile.latitude=5.556;profile.longitude=-0.182;db.session.commit();profile_id=profile.id
    return {"headers":{"Authorization":f"Bearer {body['access_token']}"},"user":body["user"],"profile_id":profile_id}
