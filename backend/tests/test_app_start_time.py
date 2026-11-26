from datetime import date, timedelta
from handework.extensions import db
from handework.models import Booking

def payload(artisan, start_time):
    return {
        "service": "Plumbing", "description": "Replace a leaking kitchen tap",
        "address": "1 Example Street", "area": "Osu", "city": "Accra",
        "contact_phone": "0244000001", "budget_type": "quote",
        "artisan_id": artisan["profile_id"],
        "scheduled_date": (date.today() + timedelta(days=4)).isoformat(),
        "start_time": start_time,
    }

def test_exact_start_time_saved(client, customer, artisan, app):
    response = client.post("/v1/bookings", json=payload(artisan, "18:30"), headers=customer["headers"])
    assert response.status_code == 201, response.get_json()
    with app.app_context():
        booking = db.session.get(Booking, response.json["id"])
        assert booking.scheduled_start.hour == 18
        assert booking.scheduled_start.minute == 30

def test_start_time_outside_6am_to_8pm_rejected(client, customer, artisan):
    for invalid in ("05:30", "20:30", "21:00", "invalid", "18:15"):
        response = client.post("/v1/bookings", json=payload(artisan, invalid), headers=customer["headers"])
        assert response.status_code == 422, (invalid, response.get_json())

def test_existing_website_window_remains_supported(client, customer, artisan):
    body = payload(artisan, "18:30")
    body.pop("start_time")
    body["time_window"] = "morning"
    response = client.post("/v1/bookings", json=body, headers=customer["headers"])
    assert response.status_code == 201
