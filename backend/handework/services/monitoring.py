import os
from threading import Lock

_lock = Lock()
_initialized = False


def initialize_monitoring():
    global _initialized

    if os.getenv("FLASK_ENV") != "production":
        return

    if os.getenv("SENTRY_ENABLED", "false").lower() != "true":
        return

    dsn = os.getenv("SENTRY_DSN")

    if not dsn:
        return

    with _lock:
        if _initialized:
            return

        import sentry_sdk
        from sentry_sdk.integrations.flask import FlaskIntegration

        def sanitize(event, hint):
            for key in (
                "request", "user", "extra",
                "breadcrumbs", "contexts", "logentry",
                "message", "transaction", "tags"
            ):
                event.pop(key, None)

            for exception in event.get("exception", {}).get("values", []):
                exception.pop("value", None)

                for frame in exception.get(
                    "stacktrace", {}
                ).get("frames", []):
                    frame.pop("vars", None)
                    frame.pop("pre_context", None)
                    frame.pop("post_context", None)
                    frame.pop("context_line", None)

            return event

        sentry_sdk.init(
            dsn=dsn,
            integrations=[FlaskIntegration()],
            environment=os.getenv(
                "SENTRY_ENVIRONMENT", "production"
            ),
            send_default_pii=False,
            include_local_variables=False,
            max_request_body_size="never",
            traces_sample_rate=0,
            before_send=sanitize
        )

        _initialized = True
