import hashlib
import hmac
import json
from handework.services.paystack import Paystack


def payable_booking(client, customer, artisan):
    created = client.post("/v1/bookings", json={"service":"Plumbing","description":"Replace a leaking kitchen tap","address":"1 Example Street","area":"Osu","city":"Accra","contact_phone":"0244000001","budget_type":"quote","budget":350,"artisan_id":artisan["profile_id"]}, headers=customer["headers"]).get_json()
    quoted = client.post(f"/v1/bookings/{created['id']}/quotes", json={"amount":300,"note":"Parts and labour"}, headers=artisan["headers"]).get_json()
    client.post(f"/v1/bookings/{created['id']}/quotes/{quoted['id']}/accept", headers=customer["headers"])
    return created["id"]


def initiate(client, customer, booking_id, monkeypatch):
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "local-test-only")
    monkeypatch.setattr(Paystack, "mobile_money_charge", lambda self, **kwargs: {"status":True,"data":{"status":"pay_offline"}})
    return client.post("/v1/payments/mobile-money", json={"booking_id":booking_id,"phone":"0244000001","network":"mtn"}, headers={**customer["headers"],"Idempotency-Key":f"payment-{booking_id}"})


def signed_webhook(client, monkeypatch, payload):
    secret="webhook-test-secret";monkeypatch.setenv("PAYSTACK_SECRET_KEY",secret);raw=json.dumps(payload,separators=(",",":")).encode();signature=hmac.new(secret.encode(),raw,hashlib.sha512).hexdigest()
    return client.post("/v1/webhooks/paystack",data=raw,content_type="application/json",headers={"x-paystack-signature":signature})


def test_signed_webhook_funds_escrow(client, customer, artisan, monkeypatch):
    booking_id=payable_booking(client,customer,artisan);payment=initiate(client,customer,booking_id,monkeypatch).get_json()
    response=signed_webhook(client,monkeypatch,{"event":"charge.success","data":{"reference":payment["reference"],"status":"success","amount":30000,"currency":"GHS"}})
    assert response.status_code==200
    booking=client.get(f"/v1/bookings/{booking_id}",headers=customer["headers"]).get_json()["booking"]
    wallet=client.get("/v1/wallet",headers=customer["headers"]).get_json()["accounts"]
    assert booking["status"]=="funded"
    assert wallet[0]["held_balance"]==300.0


def test_webhook_amount_mismatch_does_not_fund(client, customer, artisan, monkeypatch):
    booking_id=payable_booking(client,customer,artisan);payment=initiate(client,customer,booking_id,monkeypatch).get_json()
    response=signed_webhook(client,monkeypatch,{"event":"charge.success","data":{"reference":payment["reference"],"status":"success","amount":1,"currency":"GHS"}})
    assert response.status_code==200
    booking=client.get(f"/v1/bookings/{booking_id}",headers=customer["headers"]).get_json()["booking"]
    assert booking["status"]=="accepted"


def test_retry_after_provider_timeout_reuses_reference(client, customer, artisan, monkeypatch):
    booking_id = payable_booking(client, customer, artisan)
    monkeypatch.setenv("PAYSTACK_SECRET_KEY", "unit-test")
    calls = []

    def timeout(self, **data):
        calls.append(data["reference"])
        raise TimeoutError()

    monkeypatch.setattr(Paystack, "mobile_money_charge", timeout)
    payload = {"booking_id": booking_id, "phone": "0244000001", "network": "mtn"}
    for key, expected in [("initial", 502), ("retry", 202)]:
        response = client.post("/v1/payments/mobile-money", json=payload,
                               headers={**customer["headers"], "Idempotency-Key": key})
        assert response.status_code == expected
    assert calls == [response.json["reference"]]
    assert response.json["status"] == "pending"
