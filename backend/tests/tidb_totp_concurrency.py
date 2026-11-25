import os
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from datetime import datetime, timezone

import pyotp

from cryptography.fernet import Fernet
from sqlalchemy.engine import make_url
from sqlalchemy import text

source = make_url(os.environ["HANDEWORK_TEST_SOURCE_URL"])

test_url = source.set(
    database="handework_migration_test"
)

os.environ["DATABASE_URL"] = test_url.render_as_string(
    hide_password=False
)

os.environ["FLASK_ENV"] = "testing"
import secrets
os.environ["SECRET_KEY"] = secrets.token_hex(48)
os.environ["JWT_SECRET_KEY"] = secrets.token_hex(48)
os.environ["TOTP_ENABLED"] = "true"
os.environ["TOTP_ADMIN_REQUIRED"] = "false"
os.environ["TOTP_ENCRYPTION_KEY"] = Fernet.generate_key().decode()
os.environ["EMAIL_PROVIDER"] = "disabled"
os.environ["SMS_ENABLED"] = "false"
os.environ["PHONE_OTP_ENABLED"] = "false"
os.environ["PAYMENTS_ENABLED"] = "false"

from handework import create_app
from handework.extensions import db
from handework.models import User, Role, UserTotp, UserTotpRecoveryCode
from handework.services.totp import (
    create_secret,
    encrypt_secret,
    create_recovery_codes,
    hash_recovery_code
)

app = create_app(seed_development_admin=False)

app.config["TESTING"] = True
app.config["RATELIMIT_ENABLED"] = False

password = "LocalConcurrencyTest123!"
email = f"totp-test-{uuid.uuid4().hex}@example.com"

secret = create_secret()
recovery_code = create_recovery_codes(1)[0]
user_id = None


def concurrent_login(code):
    barrier = Barrier(2)

    def request_login():
        with app.test_client() as client:
            barrier.wait(timeout=20)

            response = client.post(
                "/v1/auth/login",
                json={
                    "email": email,
                    "password": password,
                    "totp_code": code
                }
            )

            body = response.get_json() or {}

            print(
                "Login diagnostic:",
                "status =", response.status_code,
                "code =", body.get("code", "none"),
                "token_issued =", bool(body.get("access_token"))
            )

            return (
                response.status_code,
                bool(body.get("access_token"))
            )

    with ThreadPoolExecutor(max_workers=2) as pool:
        first = pool.submit(request_login)
        second = pool.submit(request_login)

        results = [
            first.result(timeout=60),
            second.result(timeout=60)
        ]

    return sorted(results)


try:
    with app.app_context():

        database = db.session.execute(
            text("SELECT DATABASE()")
        ).scalar()

        assert database == "handework_migration_test"

        revision = db.session.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar()

        assert revision == "e6c27f91a842"

        assert User.query.count() == 0

        print("PASS: Isolated TiDB database confirmed")

        user = User(
            email=email,
            phone="+233244000099",
            first_name="Concurrency",
            last_name="Test",
            role=Role.CUSTOMER
        )

        user.set_password(password)

        db.session.add(user)
        db.session.flush()

        user_id = user.id

        enrollment = UserTotp(
            user_id=user_id,
            secret_encrypted=encrypt_secret(secret),
            enabled_at=datetime.now(timezone.utc)
        )

        db.session.add(enrollment)
        db.session.flush()

        db.session.add(UserTotpRecoveryCode(
            user_id=user_id,
            code_hash=hash_recovery_code(recovery_code)
        ))

        db.session.commit()

        print("PASS: Temporary test account created")

    remaining = 30 - (int(time.time()) % 30)

    if remaining < 20:
        time.sleep(remaining + 1)

    current_code = pyotp.TOTP(secret).now()

    results = concurrent_login(current_code)

    print("Concurrent authenticator results:", results)

    assert results == [
        (200, True),
        (401, False)
    ], results

    print("PASS: Concurrent authenticator replay blocked")

    results = concurrent_login(recovery_code)

    print("Concurrent recovery code results:", results)

    assert results == [
        (200, True),
        (401, False)
    ], results

    print("PASS: Concurrent recovery code reuse blocked")

    with app.app_context():

        record = UserTotpRecoveryCode.query.filter_by(
            user_id=user_id
        ).first()

        assert record.used_at is not None

        print("PASS: Recovery code consumption persisted")

finally:

    with app.app_context():

        db.session.rollback()

        database = db.session.execute(
            text("SELECT DATABASE()")
        ).scalar()

        if database == "handework_migration_test" and user_id:

            UserTotpRecoveryCode.query.filter_by(
                user_id=user_id
            ).delete()

            UserTotp.query.filter_by(
                user_id=user_id
            ).delete()

            User.query.filter_by(id=user_id).delete()

            db.session.commit()

            print("PASS: Temporary test account removed")

        db.session.remove()
        db.engine.dispose()

print("SUCCESS: TiDB concurrent authentication tests passed")
