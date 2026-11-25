import json
import os
from threading import Lock

import firebase_admin
from firebase_admin import credentials, messaging

_lock = Lock()


def enabled():
    return os.getenv(
        "FIREBASE_PUSH_ENABLED", "false"
    ).lower() in {"true", "1", "yes"}


def firebase_app():
    with _lock:
        try:
            return firebase_admin.get_app("handework")
        except ValueError:
            raw = os.getenv("FIREBASE_SERVICE_ACCOUNT_JSON")

            if not raw:
                raise RuntimeError("Firebase credentials unavailable")

            account = credentials.Certificate(json.loads(raw))

            return firebase_admin.initialize_app(
                account,
                options={"httpTimeout": 20},
                name="handework"
            )


def send_web_push(token):
    if not enabled():
        return "disabled"

    origin = os.getenv(
        "PUBLIC_WEB_URL",
        "https://handework.allmorrow.com"
    ).rstrip("/")

    message = messaging.Message(
        token=token,
        notification=messaging.Notification(
            title="handEwork",
            body="You have a new account update."
        ),
        webpush=messaging.WebpushConfig(
            headers={"TTL": "3600"},
            fcm_options=messaging.WebpushFCMOptions(
                link=origin + "/notifications"
            )
        )
    )

    try:
        messaging.send(message, app=firebase_app())
        return "accepted"
    except messaging.UnregisteredError:
        return "expired"
