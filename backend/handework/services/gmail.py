"""Authenticated delivery through the Apps Script Content Service."""
import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from urllib.parse import urlsplit

import httpx


def send_email(to, subject, text, html=None):
    url = os.getenv("EMAIL_SERVICE_URL", "")
    secret = os.getenv("EMAIL_SERVICE_SECRET")
    if (os.getenv("EMAIL_PROVIDER") != "gmail_apps_script" or not secret
            or urlsplit(url).scheme != "https"):
        return "configuration"
    fields = {"to": to, "subject": subject, "text": text}
    if html is not None:
        fields["html"] = html
    payload = json.dumps(fields, ensure_ascii=False, separators=(",", ":"))
    timestamp = str(time.time_ns() // 1_000_000)
    nonce = secrets.token_hex(16)
    digest = hmac.digest(secret.encode(), f"{timestamp}.{nonce}.{payload}".encode(), hashlib.sha256)
    envelope = {"timestamp": timestamp, "nonce": nonce, "payload": payload,
                "signature": base64.b64encode(digest).decode("ascii")}
    timeout = httpx.Timeout(15, connect=4)
    try:
        reply = httpx.post(url, json=envelope, timeout=timeout, follow_redirects=False)
    except (httpx.ConnectError, httpx.ConnectTimeout, httpx.PoolTimeout):
        return "retry"
    except httpx.RequestError:
        return "unknown"
    if reply.status_code in (302, 303):
        location = reply.headers.get("location", "")
        target = urlsplit(location)
        if target.scheme != "https" or target.hostname != "script.googleusercontent.com":
            return "unknown"
        try:
            reply = httpx.get(location, timeout=timeout, follow_redirects=False)
        except httpx.RequestError:
            return "unknown"
    if reply.status_code in (401, 403):
        return "authentication"
    if reply.status_code == 429:
        return "quota"
    try:
        result = reply.json()
    except ValueError:
        return "unknown"
    if not isinstance(result, dict):
        return "unknown"
    flags = [result[key] for key in ("ok", "success", "sent") if key in result]
    if any(type(flag) is not bool for flag in flags):
        return "unknown"
    if (result.get("error") or result.get("status") in ("error", "failed", "failure")
            or any(result.get(k) is False for k in ("ok", "success", "sent"))):
        detail = str([result.get(k) for k in ("error", "code", "message", "status")]).lower().replace("_", " ")
        if any(word in detail for word in ("quota", "too many times for one day", "daily limit")):
            return "quota"
        if any(word in detail for word in ("auth", "signature", "forbidden")):
            return "authentication"
        if result.get("retryable") is True and result.get("sent") is False:
            return "retry"
        return "rejected"
    if (reply.is_success and result.get("status", "sent") in ("sent", "success", "ok")
            and (any(result.get(k) is True for k in ("ok", "success", "sent"))
                 or result.get("status") in ("success", "sent"))):
        return "sent"
    return "unknown"
