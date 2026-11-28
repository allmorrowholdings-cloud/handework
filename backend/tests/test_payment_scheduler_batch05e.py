from datetime import datetime, timedelta, timezone
from handework.extensions import db
from handework.models import PaymentJob
from handework.routes import payment_worker

TOKEN = "t" * 40
HEADERS = {"Authorization": "Bearer " + TOKEN}
URL = "/v1/internal/payments/tick"


def setup_job(monkeypatch, kind="settlement", state="pending", attempts=0):
    monkeypatch.setenv("PAYMENT_SCHEDULER_TOKEN", TOKEN)
    monkeypatch.setenv("PAYMENT_SCHEDULER_ENABLED", "true")
    db.session.add(PaymentJob(key="test", kind=kind, record_id="record", state=state,
                              attempts=attempts, due_at=datetime.now(timezone.utc)-timedelta(minutes=1)))
    db.session.commit()


def test_auth_and_disabled(client, monkeypatch):
    monkeypatch.setenv("PAYMENT_SCHEDULER_TOKEN", TOKEN)
    monkeypatch.delenv("PAYMENT_SCHEDULER_ENABLED", raising=False)
    assert client.post(URL).status_code == 403
    assert client.post(URL, headers=HEADERS).get_json() == {"processed": 0, "enabled": False}


def test_success(client, monkeypatch):
    setup_job(monkeypatch)
    def execute(job):
        assert job.state == "running"
        return True
    monkeypatch.setattr(payment_worker, "run_job", execute)
    assert client.post(URL, headers=HEADERS).get_json()["state"] == "done"
    assert client.post(URL, headers=HEADERS).get_json()["processed"] == 0


def test_stale_claim_blocks_processing(client, monkeypatch):
    setup_job(monkeypatch, state="running")
    assert client.post(URL, headers=HEADERS).status_code == 409


def test_disabled_money_movement(client, monkeypatch):
    setup_job(monkeypatch, kind="auto_payout")
    monkeypatch.delenv("PAYMENT_AUTO_PAYOUT_ENABLED", raising=False)
    assert client.post(URL, headers=HEADERS).get_json()["processed"] == 0


def test_error_escalation(client, monkeypatch):
    setup_job(monkeypatch, attempts=4)
    def fail(job):
        raise RuntimeError("private provider detail")
    monkeypatch.setattr(payment_worker, "run_job", fail)
    result = client.post(URL, headers=HEADERS).get_json()
    assert result["state"] == "review"
    assert result["error"] == "RuntimeError"
