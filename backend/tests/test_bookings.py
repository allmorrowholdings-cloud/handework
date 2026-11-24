def booking_payload(artisan):
    return {"service":"Plumbing","description":"Replace a leaking kitchen tap","address":"1 Example Street","area":"Osu","city":"Accra","contact_phone":"0244000001","budget_type":"quote","budget":350,"artisan_id":artisan["profile_id"]}


def test_customer_creates_booking(client,customer,artisan):
    response=client.post("/v1/bookings",json=booking_payload(artisan),headers=customer["headers"])
    assert response.status_code==201
    body=response.get_json()
    assert body["reference"].startswith("VV-")
    assert body["status"]=="requested"
    notifications=client.get("/v1/notifications",headers=customer["headers"]).get_json()["items"]
    assert notifications[0]["title"]=="Booking created"


def test_invalid_status_transition_is_blocked(client,customer,artisan):
    created=client.post("/v1/bookings",json=booking_payload(artisan),headers=customer["headers"]).get_json()
    response=client.post(f"/v1/bookings/{created['id']}/status",json={"status":"completed"},headers=customer["headers"])
    assert response.status_code==403
    assert response.get_json()["code"]=="role_transition_forbidden"


def test_artisan_cannot_create_customer_booking(client,artisan):
    response=client.post("/v1/bookings",json=booking_payload(artisan),headers=artisan["headers"])
    assert response.status_code==403


def test_job_change_decisions_preserve_original_payment_amount(client, customer, artisan):
    from handework.extensions import db
    from handework.models import Booking, BookingStatus

    created = client.post("/v1/bookings", json=booking_payload(artisan), headers=customer["headers"]).get_json()
    path = f"/v1/bookings/{created['id']}"
    with client.application.app_context():
        booking = db.session.get(Booking, created["id"])
        booking.status = BookingStatus.IN_PROGRESS
        booking.agreed_amount = 350
        db.session.commit()
    assert client.post(f"{path}/changes", json={"description": "Valve", "extra_amount": "NaN"}, headers=artisan["headers"]).status_code == 422
    for decision, previous, total in [("approved", "350.00", "430.00"), ("declined", "430.00", "510.00")]:
        response = client.post(f"{path}/changes", json={"description": "Valve", "extra_amount": "80"}, headers=artisan["headers"])
        assert response.status_code == 201
        change = response.get_json()
        assert (change["current_total"], change["extra_amount"], change["new_total"]) == (previous, "80.00", total)
        endpoint = f"{path}/changes/{change['id']}/decision"
        assert client.post(endpoint, json={"decision": decision}, headers=artisan["headers"]).status_code == 403
        assert client.post(endpoint, json={"decision": decision}, headers=customer["headers"]).status_code == 200
        assert client.post(endpoint, json={"decision": decision}, headers=customer["headers"]).status_code == 409
    detail = client.get(path, headers=customer["headers"]).get_json()
    assert detail["booking"]["agreed_amount"] == 350
    assert {change["status"] for change in detail["changes"]} == {"approved", "declined"}


def test_instant_booking_requires_artisan_opt_in_and_available_date(client,customer,artisan):
    client.patch("/v1/artisans/me",json={"instant_booking":True,"starting_price":250},headers=artisan["headers"])
    client.put("/v1/artisans/me/availability",json={"items":[{"weekday":5,"start_time":"08:00","end_time":"17:00","active":True}]},headers=artisan["headers"])
    payload=booking_payload(artisan)|{"scheduled_date":"2026-08-15","instant_booking":True}
    response=client.post("/v1/bookings",json=payload,headers=customer["headers"])
    assert response.status_code==201
    assert response.get_json()["status"]=="accepted"
    detail=client.get(f"/v1/bookings/{response.get_json()['id']}",headers=customer["headers"]).get_json()
    assert detail["conversation_id"]


def test_retried_booking_creates_one_request(client, customer, artisan):
    from uuid import uuid4
    headers = {**customer["headers"], "Idempotency-Key": str(uuid4())}
    payload = booking_payload(artisan)
    first = client.post("/v1/bookings", json=payload, headers=headers)
    retry = client.post("/v1/bookings", json=payload, headers=headers)
    assert first.status_code == 201 and retry.status_code == 200
    assert retry.json["id"] == first.json["id"]
    assert len(client.get("/v1/bookings", headers=headers).json["items"]) == 1
