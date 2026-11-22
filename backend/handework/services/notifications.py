import os
import httpx


def send_expo(tokens, title, body, data=None):
    if not tokens: return []
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    if os.getenv("EXPO_ACCESS_TOKEN"): headers["Authorization"] = f"Bearer {os.environ['EXPO_ACCESS_TOKEN']}"
    messages = [{"to": token, "sound": "default", "title": title, "body": body, "data": data or {}} for token in tokens]
    response = httpx.post("https://exp.host/--/api/v2/push/send", headers=headers, json=messages, timeout=20)
    response.raise_for_status(); return response.json()


def send_sms(phone, message):
    client_id, secret = os.getenv("HUBTEL_CLIENT_ID"), os.getenv("HUBTEL_CLIENT_SECRET")
    if not client_id or not secret: raise RuntimeError("Hubtel SMS credentials are not configured")
    response = httpx.get("https://smsc.hubtel.com/v1/messages/send", params={"clientid": client_id, "clientsecret": secret, "from": os.getenv("HUBTEL_SENDER_ID", "handEwork"), "to": phone, "content": message}, timeout=20)
    response.raise_for_status(); return response.json()


def send_whatsapp(phone, message):
    url, token = os.getenv("WHATSAPP_PROVIDER_URL"), os.getenv("WHATSAPP_PROVIDER_TOKEN")
    if not url or not token: raise RuntimeError("WhatsApp provider is not configured")
    response = httpx.post(url, headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"}, json={"messaging_product": "whatsapp", "to": phone.lstrip("+"), "type": "text", "text": {"body": message}}, timeout=20)
    response.raise_for_status(); return response.json()


def queue_notifications(user, title, body, data=None, urgent=False):
    from ..extensions import db
    from ..models import Notification
    preferences = user.notification_preferences or {"push": True, "sms": True, "whatsapp": False}
    channels = ["in_app"]
    if preferences.get("push"): channels.append("push")
    if urgent and preferences.get("sms"): channels.append("sms")
    if urgent and preferences.get("whatsapp"): channels.append("whatsapp")
    rows = [Notification(user_id=user.id, channel=channel, title=title[:180], body=body[:700], data=data or {}) for channel in channels]
    db.session.add_all(rows); db.session.flush(); return [row.id for row in rows]


def dispatch_notifications(notification_ids):
    if not os.getenv("REDIS_URL"): return
    from ..tasks import deliver_notification
    for notification_id in notification_ids:
        try: deliver_notification.delay(notification_id)
        except Exception: pass
