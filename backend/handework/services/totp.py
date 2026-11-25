import base64
import io
import os
import re
import secrets
import time

import pyotp
import qrcode

from cryptography.fernet import Fernet
from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)


def totp_enabled():
    return os.getenv(
        "TOTP_ENABLED", "false"
    ).lower() in {"true", "1", "yes"}


def admin_totp_required():
    return os.getenv(
        "TOTP_ADMIN_REQUIRED", "false"
    ).lower() in {"true", "1", "yes"}


def encryption():
    key = os.getenv("TOTP_ENCRYPTION_KEY")

    if not key:
        raise RuntimeError(
            "Authenticator encryption key unavailable"
        )

    return Fernet(key.encode())


def encrypt_secret(secret):
    return encryption().encrypt(
        secret.encode()
    ).decode()


def decrypt_secret(encrypted):
    return encryption().decrypt(
        encrypted.encode()
    ).decode()


def create_secret():
    return pyotp.random_base32()


def provisioning_uri(secret, email):
    return pyotp.TOTP(secret).provisioning_uri(
        name=email,
        issuer_name=os.getenv(
            "TOTP_ISSUER", "handEwork"
        )
    )


def create_qr_code(uri):
    image = qrcode.make(uri)
    output = io.BytesIO()
    image.save(output, format="PNG")

    return (
        "data:image/png;base64," +
        base64.b64encode(
            output.getvalue()
        ).decode()
    )


def matching_step(secret, code, last_used_step=None, now=None):
    if not re.fullmatch(r"[0-9]{6}", str(code)):
        return None

    current = int(
        time.time() if now is None else now
    ) // 30

    generator = pyotp.TOTP(secret)

    for step in (current, current - 1, current + 1):
        if (
            last_used_step is not None
            and step <= last_used_step
        ):
            continue

        expected = generator.at(step * 30)

        if secrets.compare_digest(expected, str(code)):
            return step

    return None


def create_recovery_codes(count=10):
    codes = []

    for _ in range(count):
        raw = secrets.token_hex(8).upper()

        codes.append(
            "-".join(
                raw[i:i+4]
                for i in range(0, 16, 4)
            )
        )

    return codes


def normalize_recovery_code(code):
    normalized = str(code).replace(
        "-", ""
    ).replace(" ", "").upper()

    if not re.fullmatch(r"[A-F0-9]{16}", normalized):
        return None

    return normalized


def hash_recovery_code(code):
    normalized = normalize_recovery_code(code)

    if not normalized:
        raise ValueError("Invalid recovery code")

    return generate_password_hash(
        normalized,
        method="scrypt"
    )


def verify_recovery_code(code_hash, supplied):
    normalized = normalize_recovery_code(supplied)

    if not normalized:
        return False

    return check_password_hash(
        code_hash,
        normalized
    )

def authenticate_second_factor(row, supplied):
    from datetime import datetime, timedelta, timezone

    from ..extensions import db
    from ..models import UserTotp, UserTotpRecoveryCode
    from sqlalchemy import or_

    now = datetime.now(timezone.utc)

    if row.locked_until:
        locked_until = row.locked_until

        if locked_until.tzinfo is None:
            locked_until = locked_until.replace(
                tzinfo=timezone.utc
            )

        if locked_until > now:
            return "locked"

        row.failed_attempts = 0
        row.locked_until = None

    accepted = False

    if re.fullmatch(r"[0-9]{6}", supplied):
        secret = decrypt_secret(row.secret_encrypted)

        step = matching_step(
            secret,
            supplied,
            row.last_used_step
        )

        if step is not None:
            consumed = UserTotp.query.filter(
                UserTotp.user_id == row.user_id,
                UserTotp.enabled_at.is_not(None),
                or_(
                    UserTotp.last_used_step.is_(None),
                    UserTotp.last_used_step < step
                )
            ).update(
                {"last_used_step": step},
                synchronize_session=False
            )

            accepted = consumed == 1

    elif normalize_recovery_code(supplied):
        records = UserTotpRecoveryCode.query.filter_by(
            user_id=row.user_id,
            used_at=None
        ).all()

        for record in records:
            if verify_recovery_code(
                record.code_hash,
                supplied
            ):
                consumed = UserTotpRecoveryCode.query.filter(
                    UserTotpRecoveryCode.id == record.id,
                    UserTotpRecoveryCode.user_id == row.user_id,
                    UserTotpRecoveryCode.used_at.is_(None)
                ).update(
                    {"used_at": now},
                    synchronize_session=False
                )

                accepted = consumed == 1

                break

    if accepted:
        row.failed_attempts = 0
        row.locked_until = None
        return "accepted"

    row.failed_attempts += 1

    if row.failed_attempts >= 5:
        row.locked_until = now + timedelta(minutes=15)

    return "invalid"
