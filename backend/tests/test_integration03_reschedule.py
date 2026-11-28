from test_complete_integration import future_day, hours, payload


def test_reschedule_before_quote(client, customer, artisan):
    hours(client, artisan)
    result = client.post("/v1/bookings", json=payload(artisan), headers=customer["headers"])
    assert result.status_code == 201
    path = f"/v1/bookings/{result.json['id']}"
    data = {"scheduled_date": future_day().isoformat(), "start_time": "10:00"}
    assert client.post(path+"/reschedule", json=data, headers=artisan["headers"]).status_code == 403
    assert client.post(path+"/reschedule", json={**data,"start_time":"12:00"}, headers=customer["headers"]).status_code == 409
    assert client.post(path+"/reschedule", json={**data,"start_time":"10:15"}, headers=customer["headers"]).status_code == 422
    updated = client.post(path+"/reschedule", json=data, headers=customer["headers"])
    assert updated.status_code == 200
    assert "T10:00" in updated.json["booking"]["scheduled_start"]
    assert client.post(path+"/quotes", json={"amount":100}, headers=artisan["headers"]).status_code == 201
    assert client.post(path+"/reschedule", json=data, headers=customer["headers"]).status_code == 409
