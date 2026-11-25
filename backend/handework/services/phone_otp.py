import os
import re

import httpx

from .arkesel import normalize_phone


def otp_enabled():
    return os.getenv(
        "PHONE_OTP_ENABLED", "false"
    ).lower() in {"true", "1", "yes"}


def otp_request(action, payload):
    if not otp_enabled():
        raise RuntimeError("Phone verification is disabled")

    key = os.getenv("ARKESEL_OTP_API_KEY")
    if not key:
        raise RuntimeError("OTP credentials are unavailable")

    if action not in {"generate", "verify"}:
        raise ValueError("Invalid OTP action")

    response = httpx.post(
        "https://sms.arkesel.com/api/otp/" + action,
        headers={
            "api-key": key,
            "Accept": "application/json"
        },
        json=payload,
        timeout=15
    )

    response.raise_for_status()
    result = response.json()

    if not isinstance(result, dict):
        raise RuntimeError("Invalid OTP provider response")

    return str(result.get("code", ""))


def generate_otp(phone):
    number = normalize_phone(phone)

    if not number.startswith("233"):
        raise ValueError("Only Ghanaian numbers are supported")

    return otp_request("generate", {
        "expiry": 5,
        "length": 6,
        "medium": "sms",
        "message": "Your handEwork verification code is %otp_code%. Do not share this code.",
        "number": number,
        "sender_id": os.getenv(
            "ARKESEL_SENDER_ID", "handEwork"
        ),
        "type": "numeric"
    }) == "1000"


def verify_otp(phone, code):
    if not re.fullmatch(r"[0-9]{6}", str(code)):
        return False

    return otp_request("verify", {
        "number": normalize_phone(phone),
        "code": str(code)
    }) == "1100"
