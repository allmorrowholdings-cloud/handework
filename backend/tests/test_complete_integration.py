from datetime import date, timedelta
from handework.extensions import db
from handework.models import ArtisanProfile, User


def future_day():
    return date.today() + timedelta(days=7)


def hours(client, artisan):
    row = {"weekday": future_day().weekday(), "start_time": "09:00", "end_time": "12:00", "active": True}
    endpoint = "/v1/artisans/me/availability"
    assert client.put(endpoint, json={"items": [row]}, headers=artisan["headers"]).status_code == 200
    return row


def test_invalid_hours_preserve_existing_schedule(client, artisan):
    row = hours(client, artisan)
    endpoint = "/v1/artisans/me/availability"
    for invalid in [[row, row], [{**row, "end_time": "08:00"}], [{**row, "active": "false"}], [{**row, "weekday": 7}], [{**row, "start_time": "garbage"}]]:
        assert client.put(endpoint, json={"items": invalid}, headers=artisan["headers"]).status_code == 422
        assert client.get(endpoint, headers=artisan["headers"]).json["items"] == [row]


def test_search_respects_exact_working_hours(client, artisan):
    hours(client, artisan)
    query = {"service": "Plumbing", "date": future_day().isoformat(), "coordinates": "5.556,-0.182"}
    endpoint = "/v1/artisans/search"
    assert client.get(endpoint, query_string={**query, "start_time": "09:00"}).json["items"]
    assert client.get(endpoint, query_string={**query, "start_time": "12:00"}).json["items"] == []
    assert client.get(endpoint, query_string={**query, "start_time": "bad"}).status_code == 422
    assert client.get(endpoint, query_string={"start_time": "09:00"}).status_code == 422


def payload(artisan):
    return {"service": "Plumbing", "description": "Repair tap", "address": "Example", "area": "Osu", "city": "Accra", "contact_phone": "0244000001", "artisan_id": artisan["profile_id"], "scheduled_date": future_day().isoformat(), "start_time": "09:00"}


def test_direct_booking_and_quote_recheck_hours(client, customer, artisan):
    row = hours(client, artisan)
    data = payload(artisan)
    assert client.post("/v1/bookings", json={**data,"start_time":"12:00"}, headers=customer["headers"]).status_code == 409
    result = client.post("/v1/bookings", json=data, headers=customer["headers"])
    assert result.status_code == 201
    path = f"/v1/bookings/{result.json['id']}/quotes"
    quote = client.post(path, json={"amount": 100}, headers=artisan["headers"])
    assert quote.status_code == 201
    assert client.put("/v1/artisans/me/availability", json={"items":[{**row,"active":False}]}, headers=artisan["headers"]).status_code == 200
    assert client.post(path+f"/{quote.json['id']}/accept", headers=customer["headers"]).status_code == 409


def test_readiness_and_suspended_public_workproof(client, artisan, app):
    assert client.get("/v1/artisans/me", headers=artisan["headers"]).json["artisan"]["readiness"]["ready"]
    with app.app_context():
        profile = db.session.get(ArtisanProfile, artisan["profile_id"])
        profile.user.status = "suspended"
        db.session.commit()
    assert client.get(f"/v1/workproof/{artisan['profile_id']}").status_code == 404
