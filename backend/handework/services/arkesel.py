import os
import re

import httpx


def sms_enabled():
    return os.getenv("SMS_ENABLED", "false").lower() in {
        "true", "1", "yes"
    }


def normalize_phone(phone):
    number = re.sub(r"[\s()\-]", "", str(phone or ""))
    if number.startswith("00"):
        number = "+" + number[2:]
    if re.fullmatch(r"0[0-9]{9}", number):
        number = "+233" + number[1:]
    if re.fullmatch(r"233[0-9]{9}", number):
        number = "+" + number
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", number):
        raise ValueError("Invalid recipient phone number")
    return number.lstrip("+")


def send_sms(phone, message):
    if not sms_enabled():
        raise RuntimeError("SMS delivery is disabled")

    if os.getenv("SMS_PROVIDER", "").lower() != "arkesel":
        raise RuntimeError("SMS provider is not configured")

    key = os.getenv("ARKESEL_API_KEY")
    sender = os.getenv("ARKESEL_SENDER_ID", "handEwork")
    base_url = os.getenv(
        "ARKESEL_BASE_URL",
        "https://sms.arkesel.com"
    ).rstrip("/")

    if not key:
        raise RuntimeError("Arkesel API key is not configured")

    if base_url != "https://sms.arkesel.com":
        raise RuntimeError("Invalid Arkesel API URL")

    if not sender or len(sender) > 11:
        raise ValueError("Invalid Arkesel sender ID")

    recipient = normalize_phone(phone)

    response = httpx.post(
        base_url + "/api/v2/sms/send",
        headers={
            "api-key": key,
            "Accept": "application/json"
        },
        json={
            "sender": sender,
            "message": message,
            "recipients": [recipient]
        },
        timeout=20
    )

    response.raise_for_status()
    result = response.json()

    if result.get("status") != "success":
        raise RuntimeError("Arkesel rejected SMS request")

    records = result.get("data", [])
    if isinstance(records, dict):
        records = [records]

    if not isinstance(records, list) or not any(
        isinstance(item, dict) and item.get("id")
        for item in records
    ):
        raise RuntimeError("Arkesel acceptance not confirmed")

    return result
