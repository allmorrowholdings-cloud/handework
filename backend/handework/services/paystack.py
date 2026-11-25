import hashlib
import hmac
import os
from decimal import Decimal
from urllib.parse import urlsplit
import httpx

NETWORKS = {"mtn": "mtn", "telecel": "vod", "vodafone": "vod", "airteltigo": "atl", "atmoney": "atl", "airtel": "atl"}


def enabled(name):
    return os.getenv(name, "").strip().lower() == "true"


def checkout_enabled(user, booking=None):
    if enabled("PAYMENTS_ENABLED"):
        return True
    testers = os.getenv("PAYMENT_TEST_USER_IDS", "").split(",")
    if user.id in testers and os.getenv("PAYSTACK_SECRET_KEY", "").startswith("sk_test_"):
        return True
    return bool(booking and enabled("PAYMENT_LIVE_PILOT_ENABLED") and user.id in testers
                and booking.id in os.getenv("PAYMENT_LIVE_PILOT_BOOKINGS", "").split(","))


def minor(amount):
    return int(Decimal(str(amount)) * 100)


def matches(data, reference, amount, currency):
    return (data.get("reference") == reference and data.get("currency") == currency
            and type(data.get("amount")) is int and data["amount"] == minor(amount))


def checkout_url(data):
    url = data.get("authorization_url") or ""
    parsed = urlsplit(url)
    return url if parsed.scheme == "https" and parsed.netloc == "checkout.paystack.com" else None


class Paystack:
    def __init__(self):
        self.secret = os.getenv("PAYSTACK_SECRET_KEY", "")
        self.base = "https://api.paystack.co"

    def call(self, method, path, **kwargs):
        if not self.secret:
            raise RuntimeError("Paystack is unavailable")
        response = httpx.request(method, self.base + path, headers={"Authorization": f"Bearer {self.secret}"},
                                 timeout=15, **kwargs)
        response.raise_for_status()
        body = response.json()
        if body.get("status") is not True:
            raise RuntimeError("Provider did not accept request")
        return body

    def mobile_money_charge(self, *, email, amount_ghs, phone, network, reference):
        provider = NETWORKS.get(network.lower().replace(" ", ""))
        if not provider:
            raise ValueError("Unsupported mobile-money network")
        return self.call("POST", "/charge", json={"email": email, "amount": minor(amount_ghs),
                         "currency": "GHS", "reference": reference,
                         "mobile_money": {"phone": phone, "provider": provider}})

    def initialize_transaction(self, *, email, amount_ghs, reference, callback_url=None, metadata=None):
        payload = {"email": email, "amount": minor(amount_ghs), "currency": "GHS",
                   "reference": reference, "channels": ["card", "mobile_money"]}
        if callback_url:
            payload["callback_url"] = callback_url
        if metadata:
            payload["metadata"] = metadata
        return self.call("POST", "/transaction/initialize", json=payload)

    def verify_transaction(self, reference):
        return self.call("GET", f"/transaction/verify/{reference}")

    def verify_signature(self, raw_body, signature):
        if not self.secret:
            raise RuntimeError("Paystack webhook is unavailable")
        expected = hmac.new(self.secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return len(signature) == 128 and signature.isascii() and hmac.compare_digest(expected, signature)
