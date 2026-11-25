import hashlib
import hmac
import json
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from handework.extensions import db
from handework.models import (Booking, BookingStatus, FileAsset, JournalPosting, LedgerEntry, Notification,
                              Payment, PaymentJob, PaymentOperation, PaymentReceipt, PayoutRecipient, Role, User, WalletAccount)
from handework.services.paystack import Paystack
from test_payments import initiate, payable_booking, signed_webhook


@pytest.fixture()
def admin(client):
    result = client.post("/v1/auth/register", json={"first_name":"Ops","last_name":"Test","email":"ops@example.com",
                         "phone":"0244000003","password":"StrongPass123"}).json
    db.session.get(User,result["user"]["id"]).role = Role.ADMIN
    db.session.commit()
    return {"Authorization":"Bearer "+result["access_token"]}


def funded(client, customer, artisan, monkeypatch):
    booking = payable_booking(client,customer,artisan)
    result = initiate(client,customer,booking,monkeypatch).json
    event = {"event":"charge.success","data":{"reference":result["reference"],"amount":30000,"currency":"GHS","status":"success"}}
    for _ in range(2):
        assert signed_webhook(client,monkeypatch,event).status_code == 200
    assert LedgerEntry.query.count()==1
    assert PaymentReceipt.query.count()==1
    return booking, result["payment_id"]


def complete(client,booking,artisan):
    for status in ["en_route","in_progress","completion_submitted"]:
        assert client.post(f"/v1/bookings/{booking}/status", headers=artisan["headers"],json={"status":status}).status_code==200


def test_flag_and_signature(client,customer,artisan,monkeypatch):
    booking = payable_booking(client,customer,artisan)
    monkeypatch.setenv("PAYSTACK_SECRET_KEY","unit-secret")
    assert client.post("/v1/payments/checkout",headers=customer["headers"],json={"booking_id":booking}).status_code==503
    assert client.post("/v1/shop/orders",headers=customer["headers"],json={}).status_code==503
    assert client.post("/v1/webhooks/paystack",json={},headers={"x-paystack-signature":"invalid"}).status_code==401
    assert Payment.query.count()==PaymentReceipt.query.count()==0


def test_failed_verification_and_wrong_reference(client,customer,artisan,monkeypatch):
    booking = payable_booking(client,customer,artisan)
    result=initiate(client,customer,booking,monkeypatch).json
    ref=result["reference"]
    verified={"reference":"unrelated","amount":30000,"currency":"GHS","status":"success"}
    monkeypatch.setattr(Paystack,"verify_transaction",lambda *a:{"data":verified})
    path=f"/v1/payments/{result['payment_id']}/verify"
    assert client.post(path,headers=customer["headers"]).json["status"]=="pending"
    verified.update(reference=ref,status="failed")
    assert client.post(path,headers=customer["headers"]).json["status"]=="failed"
    assert WalletAccount.query.count()==0


def test_partial_refund_release_and_transfer_failure(client,customer,artisan,admin,monkeypatch):
    monkeypatch.setenv('EMAIL_PROVIDER', 'gmail_apps_script')
    booking,pid=funded(client,customer,artisan,monkeypatch)
    payment=db.session.get(Payment,pid)
    state={"transfer":"failed","refund_id":11}
    def provider(self,method,path,**opts):
        if path=="/refund":
            state["refund"]=opts["json"]
            return {"data":{"id":state["refund_id"]}}
        if path=="/refund/11":
            return {"data":{"id":11,"merchant_note":state["refund"]["merchant_note"],"amount":5000,"currency":"GHS",
                            "transaction":{"reference":payment.provider_reference},"status":"processed"}}
        if path=="/settlement":
            return {"data":[{"id":8,"status":"success"}]}
        if path=="/settlement/8/transactions":
            return {"data":[{"reference":payment.provider_reference,"amount":30000,"currency":"GHS","fees":100}]}
        if path=="/bank/resolve":
            return {"data":{"account_number":"0244000002","account_name":"Kojo Test"}}
        if path=="/transferrecipient":
            return {"data":{"recipient_code":"RCP_test","currency":"GHS","active":True,
                            "details":{"account_number":"0244000002","bank_code":"MTN"}}}
        if path=="/transfer":
            state["payout"]=opts["json"]
            return {"data":{"reference":opts["json"]["reference"],"status":"pending"}}
        if path.startswith("/transfer/verify/"):
            return {"data":{**state["payout"],"recipient":{"recipient_code":"RCP_test"},"status":state["transfer"]}}
        raise AssertionError(path)
    monkeypatch.setattr(Paystack,"call",provider)
    path=f"/v1/payments/{pid}"
    assert client.post(path+"/refund",json={"amount":50},headers=customer["headers"]).status_code==403
    headers={**admin,"Idempotency-Key":"refund-first"}
    for _ in range(2):
        r=client.post(path+"/refund",headers=headers,json={"password":"StrongPass123","amount":"50.00"})
        assert r.status_code in {200,202}
    refund=r.json["id"]
    for _ in range(2):
        assert client.post(f"/v1/admin/payment-operations/{refund}/reconcile",headers=admin).json["status"]=="success"
    assert WalletAccount.query.filter_by(user_id=customer["user"]["id"]).one().held_balance==250
    complete(client,booking,artisan)
    assert client.post(f"/v1/bookings/{booking}/release",headers=customer["headers"]).json["released_amount"]==220
    assert client.post(f"/v1/bookings/{booking}/release",headers=customer["headers"]).status_code==409
    assert client.post(path+"/settlement",headers=admin,json={"settlement_id":8}).status_code==200
    r=client.post("/v1/artisan/payout-recipient",headers=artisan["headers"],json={"type":"mobile_money","account_number":"0244000002","bank_code":"MTN","password":"StrongPass123"})
    assert r.status_code==200
    monkeypatch.setenv("PAYSTACK_TRANSFERS_ENABLED","true")
    def payout(key):
        return client.post(path+"/payout",headers={**admin,"Idempotency-Key":key},json={"password":"StrongPass123"})
    for key,status in [("attempt1","failed"),("attempt2","success")]:
        state["transfer"]=status
        r=payout(key)
        assert r.status_code==202
        assert payout(key+"-other").status_code==409
        op=r.json["id"]
        for _ in range(2):
            assert client.post(f"/v1/admin/payment-operations/{op}/reconcile",headers=admin).json["status"]==status
    snapshot=client.get("/v1/wallet",headers=artisan["headers"]).json["accounts"][0]
    assert snapshot["transferred"]==220 and snapshot["available_balance"]==0
    state["transfer"]="reversed"
    assert client.post(f"/v1/admin/payment-operations/{op}/reconcile",headers=admin).json["status"]=="reversed"
    assert client.get("/v1/wallet",headers=artisan["headers"]).json["accounts"][0]["available_balance"]==220
    assert JournalPosting.query.filter_by(event="commission").one().units==3000
    payouts = Notification.query.filter_by(channel="email", title="Payout updated", user_id=artisan["user"]["id"]).all()
    assert sorted(item.body.split()[-1] for item in payouts) == ["failed.", "reversed.", "success."]
    for account in (customer, artisan):
        assert Notification.query.filter_by(channel="email", title="Payment confirmed", user_id=account["user"]["id"]).count() == 1


def test_auto_release_gates(client,customer,artisan,monkeypatch):
    from handework.routes.payment_worker import auto_release
    from handework.routes.payments import control_for
    booking,pid=funded(client,customer,artisan,monkeypatch)
    complete(client,booking,artisan)
    monkeypatch.setenv("PAYMENT_AUTO_RELEASE_ENABLED","true")
    assert not auto_release(booking)
    p=db.session.get(Payment,pid)
    c=control_for(p)
    c.auto_hours,c.settlement_id=48,"42"
    db.session.add(PayoutRecipient(artisan_id=p.artisan_id,code="RCP_selected",last_four="1234"))
    db.session.add(FileAsset(owner_id=artisan["user"]["id"],booking_id=booking,purpose="completion_evidence",mime_type="image/jpeg",url="s3://test/job/photo"))
    notice=Notification.query.filter_by(user_id=customer["user"]["id"],channel="in_app",title="Booking updated").order_by(Notification.created_at.desc()).first()
    notice.read_at=datetime.now(timezone.utc)
    db.session.commit()
    assert not auto_release(booking)
    from handework.models import BookingStatusEvent
    past=datetime.now(timezone.utc)-timedelta(hours=49)
    BookingStatusEvent.query.filter_by(booking_id=booking,to_status="completion_submitted").one().occurred_at=past
    FileAsset.query.filter_by(booking_id=booking).one().created_at=past
    notice.created_at=past
    notice.read_at=past
    db.session.commit()
    monkeypatch.setattr(Paystack,"call",lambda *a,**k:{"data":[{"currency":"GHS","balance":30000}]})
    c.provider_hold=True
    db.session.commit()
    assert not auto_release(booking)
    c.provider_hold=False
    evidence = FileAsset.query.filter_by(booking_id=booking).one()
    evidence.deleted_at = datetime.now(timezone.utc)
    from handework.models import DriveSubmission
    db.session.add(DriveSubmission(owner_id=artisan["user"]["id"], purpose="portfolio", title="Finished job",
                                  url="https://drive.google.com/file/d/example/view", item_kind="file",
                                  drive_id="example", status="approved"))
    db.session.commit()
    assert not auto_release(booking)
    evidence.deleted_at = None
    db.session.commit()
    assert auto_release(booking)
    assert auto_release(booking)
    assert JournalPosting.query.filter_by(event="release").count()==1


def test_dispute_blocks_release(client,customer,artisan,monkeypatch):
    booking,_=funded(client,customer,artisan,monkeypatch)
    complete(client,booking,artisan)
    assert client.post("/v1/disputes",headers=customer["headers"],json={"booking_id":booking,"reason":"quality","description":"Incomplete finish"}).status_code==201
    assert client.post(f"/v1/bookings/{booking}/release",headers=customer["headers"]).status_code==409
    assert JournalPosting.query.filter_by(event="release").count()==0
