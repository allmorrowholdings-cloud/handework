import hashlib
import hmac
import os
import httpx

NETWORKS = {"mtn": "mtn", "telecel": "vod", "vodafone": "vod", "airteltigo": "atl", "atmoney": "atl", "airtel": "atl"}


class Paystack:
    def __init__(self):
        self.secret = os.getenv("PAYSTACK_SECRET_KEY", "")
        self.base = os.getenv("PAYSTACK_BASE_URL", "https://api.paystack.co").rstrip("/")

    def _headers(self):
        if not self.secret: raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")
        return {"Authorization": f"Bearer {self.secret}", "Content-Type": "application/json"}

    def mobile_money_charge(self, *, email, amount_ghs, phone, network, reference):
        provider = NETWORKS.get(network.lower().replace(" ", ""))
        if not provider: raise ValueError("Unsupported mobile-money network")
        payload = {"email": email, "amount": int(round(float(amount_ghs) * 100)), "currency": "GHS", "reference": reference, "mobile_money": {"phone": phone, "provider": provider}}
        response = httpx.post(f"{self.base}/charge", headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status(); return response.json()


    def initialize_transaction(self, *, email, amount_ghs, reference, callback_url=None, metadata=None):
        payload = {
            "email": email,
            "amount": int(round(float(amount_ghs) * 100)),
            "currency": "GHS",
            "reference": reference,
        }
        if callback_url:
            payload["callback_url"] = callback_url
        if metadata:
            payload["metadata"] = metadata
        response = httpx.post(f"{self.base}/transaction/initialize", headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def verify_transaction(self, reference):
        response = httpx.get(f"{self.base}/transaction/verify/{reference}", headers=self._headers(), timeout=30)
        response.raise_for_status()
        return response.json()

    def refund(self, transaction_reference, amount_ghs=None):
        payload = {"transaction": transaction_reference}
        if amount_ghs is not None: payload["amount"] = int(round(float(amount_ghs) * 100))
        response = httpx.post(f"{self.base}/refund", headers=self._headers(), json=payload, timeout=30)
        response.raise_for_status(); return response.json()

    def verify_signature(self, raw_body, signature):
        if not self.secret: raise RuntimeError("PAYSTACK_SECRET_KEY is not configured")
        expected = hmac.new(self.secret.encode(), raw_body, hashlib.sha512).hexdigest()
        return bool(signature) and hmac.compare_digest(expected, signature)
