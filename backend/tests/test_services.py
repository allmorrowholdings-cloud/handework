import hashlib
import hmac
import pytest
from handework.services.distance import haversine_km
from handework.services.matching import matching_score
from handework.services.paystack import Paystack


def test_haversine_distance_is_realistic():
    distance=haversine_km(5.6037,-0.1870,6.6885,-1.6244)
    assert 180<distance<260


def test_matching_respects_radius_and_availability():
    assert matching_score(text_match=1,distance_km=11,radius_km=10,rating=5,completion_rate=100,available=True)==0
    assert matching_score(text_match=1,distance_km=1,radius_km=10,rating=5,completion_rate=100,available=False)==0
    assert matching_score(text_match=1,distance_km=1,radius_km=10,rating=5,completion_rate=100,available=True)>80


def test_paystack_signature(monkeypatch):
    monkeypatch.setenv("PAYSTACK_SECRET_KEY","test_secret")
    body=b'{"event":"charge.success"}'
    signature=hmac.new(b"test_secret",body,hashlib.sha512).hexdigest()
    assert Paystack().verify_signature(body,signature)
    assert not Paystack().verify_signature(body,"wrong")


def test_paystack_signature_requires_secret(monkeypatch):
    monkeypatch.delenv("PAYSTACK_SECRET_KEY",raising=False)
    with pytest.raises(RuntimeError):
        Paystack().verify_signature(b"{}", "signature")
