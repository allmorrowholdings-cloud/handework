"""Exercise independent HTTP requests, sessions and connections against the same DB."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Lock
import hashlib
import hmac
import json
import os
from uuid import uuid4

from handework import create_app
from handework.config import TestConfig
from handework.extensions import db
from handework.models import ArtisanProfile, JournalPosting, LedgerEntry, Payment, PaymentReceipt
from handework.services.paystack import Paystack
from test_payments import payable_booking


def test_competing_checkouts_and_webhooks(tmp_path, monkeypatch):
    class Config(TestConfig):
        SQLALCHEMY_DATABASE_URI = ("mysql+pymysql://root@127.0.0.1:33327/handework_payment_qa_final"
                                  if os.getenv("PAYMENT_QA_MYSQL")=="true" else "sqlite:///"+str(tmp_path/"threads.db"))
    app = create_app(Config,seed_development_admin=False)
    with app.app_context():
        db.create_all()
    client=app.test_client()
    participants=[]
    suffix=uuid4().hex[:8]
    for i,route in enumerate(["register","register-artisan"]):
        data={"first_name":"Test","last_name":"User","email":f"{i}-{suffix}@example.com","password":"StrongPass123",
              "phone":f"024{int(suffix,16)%1000000:06d}{i}","trade":"Plumber","city":"Accra","area":"Osu",
              "years_experience":3,"radius_km":10}
        response=client.post("/v1/auth/"+route,json=data).json
        participants.append({"headers":{"Authorization":"Bearer "+response["access_token"]},"user":response["user"]})
    customer,artisan=participants
    with app.app_context():
        profile=ArtisanProfile.query.filter_by(user_id=artisan["user"]["id"]).one()
        profile.verification_status="approved"
        profile.available=True
        artisan["profile_id"]=profile.id
        db.session.commit()
    booking=payable_booking(client,customer,artisan)
    monkeypatch.setenv("PAYMENTS_ENABLED","true")
    monkeypatch.setenv("PAYSTACK_SECRET_KEY","isolated-test")
    calls=[]
    mutex=Lock()
    def charge(self,**kw):
        with mutex:
            calls.append(kw["reference"])
        return {"data":{"reference":kw["reference"],"status":"pending"}}
    monkeypatch.setattr(Paystack,"mobile_money_charge",charge)
    def race(fn):
        gate=Barrier(2)
        def task(i):
            with app.test_client() as c:
                gate.wait(timeout=20)
                return fn(c,i)
        with ThreadPoolExecutor(max_workers=2) as pool:
            return list(pool.map(task,[0,1]))
    statuses=race(lambda c,i:c.post("/v1/payments/mobile-money",headers={**customer["headers"],"Idempotency-Key":suffix+str(i)},
                       json={"booking_id":booking,"network":"mtn"}).status_code)
    assert all(s in {200,202,409} for s in statuses) and len(calls)==1
    event={"event":"charge.success","data":{"reference":calls[0],"amount":30000,"currency":"GHS","status":"success"}}
    monkeypatch.setattr(Paystack,"verify_transaction",lambda *args:{"data":event["data"]})
    raw=json.dumps(event).encode()
    sig=hmac.new(b"isolated-test",raw,hashlib.sha512).hexdigest()
    assert race(lambda c,i:c.post("/v1/webhooks/paystack",data=raw,content_type="application/json",
                                  headers={"x-paystack-signature":sig}).status_code)==[200,200]
    # Fresh application instance verifies committed state after restart.
    restarted=create_app(Config,seed_development_admin=False)
    with restarted.app_context():
        payment=Payment.query.filter_by(booking_id=booking).one()
        assert payment.status.value=="held"
        assert LedgerEntry.query.filter_by(payment_id=payment.id).count()==1
        assert JournalPosting.query.filter_by(reference=payment.id,event="collection").count()==1
        assert db.session.get(PaymentReceipt,hashlib.sha256(raw).hexdigest())
