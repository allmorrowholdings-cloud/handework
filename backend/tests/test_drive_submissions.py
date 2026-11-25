import pytest
from handework.extensions import db
from handework.models import Course, DriveSubmission, FileAsset, Notification, Role, TrainingProvider, User, WorkProofEvidence
from handework.services.drive_links import parse_drive_link

FILE = "https://drive.google.com/file/d/sample_123-ABC/view"
FOLDER = "https://drive.google.com/drive/folders/folder_123"
BASE = "/v1/drive-submissions"
ADMIN = "/v1/admin/drive-submissions"


@pytest.mark.parametrize(("url", "normalized", "kind"), [
    (FILE + "?usp=sharing&resourcekey=0-abc", FILE + "?resourcekey=0-abc", "file"),
    (FOLDER.replace("/folders", "/u/1/folders") + "?usp=drive_link", FOLDER, "folder"),
    ("https://docs.google.com/spreadsheets/d/ABC123/edit#gid=0", "https://docs.google.com/spreadsheets/d/ABC123/edit", "file"),
    ("https://drive.google.com/open?id=item123&usp=sharing", "https://drive.google.com/open?id=item123", "item"),
])
def test_drive_viewer_links(url, normalized, kind):
    assert parse_drive_link(url)[:2] == (normalized, kind)


@pytest.mark.parametrize("url", [
    None, "http://drive.google.com/file/d/abc/view", FILE.replace(".com/", ".com.example/"),
    FILE.replace(".com/", ".com:8443/"), FILE.replace(".com/", ".com@other.test/"),
    FILE.replace(".com/", ".com\\@other.test/"), FILE + "?continue=https://example.com",
    FILE.replace("file/d", "redirect/d"), FILE.replace("sample_123-ABC", "%2f%2fexample.com"),
    "https://drive.google.com/open?id=a&id=b", FILE + "\n", FILE + "#https://example.com",
    "https://docs.google.com/document/d/e/published/pub", "https://drive.google.com/drive/folders/",
    "https://drive.google.com/uc?export=download&id=123", "https://example.com/redirect-to-drive",
])
def test_reject_non_viewer_links(url):
    with pytest.raises(ValueError):
        parse_drive_link(url)


@pytest.fixture
def admin(client):
    result = client.post("/v1/auth/register", json={"first_name":"Review","last_name":"Admin","email":"review@example.com",
                         "phone":"0244000003","password":"StrongPass123"}).json
    db.session.get(User, result["user"]["id"]).role = Role.ADMIN
    db.session.commit()
    return {"Authorization": "Bearer " + result["access_token"]}


def submit(client, headers, purpose, **fields):
    return client.post(BASE, headers=headers, json={"title":"Example", "url":FILE, "purpose":purpose, **fields})


def review(client, headers, item, decision="approved"):
    return client.post(f"{ADMIN}/{item['id']}/review", headers=headers,
                       json={"version": item["version"], "status":decision, "note":"Review completed"})


def test_portfolio_lifecycle_and_stale_decisions(client, artisan, customer, admin, monkeypatch):
    monkeypatch.setenv("EMAIL_PROVIDER", "gmail_apps_script")
    assert client.get(BASE).status_code == 401
    assert submit(client, customer["headers"], "portfolio").status_code == 403
    response = submit(client, artisan["headers"], "portfolio", owner_id=customer["user"]["id"], status="approved")
    assert response.status_code == 201
    item = response.json["item"]
    path = BASE + "/" + item["id"]
    def profile():
        return client.get("/v1/artisans/" + artisan["profile_id"]).json

    assert item["status"] == "pending" and item["source"] == "google_drive" and item["access_checked"] is False
    assert item["owner_id"] == artisan["user"]["id"]
    assert profile()["external_portfolio"] == []
    assert client.get(BASE, headers=customer["headers"]).json["items"] == []
    assert client.put(path, headers=customer["headers"], json={"version":1,"url":FOLDER}).status_code == 404
    assert client.delete(path, headers=customer["headers"], json={"version":1}).status_code == 404
    assert review(client, artisan["headers"], item).status_code == 403
    assert client.get(ADMIN, headers=admin).json["items"][0]["owner_name"]
    approved = review(client, admin, item).json["item"]
    assert review(client, admin, item).status_code == 409
    public = profile()
    assert public["external_portfolio"][0]["url"] == FILE and public["portfolio"] == []
    assert public["workproof"]["verified_jobs"] == 0 and WorkProofEvidence.query.count() == FileAsset.query.count() == 0
    assert Notification.query.filter_by(channel="email", user_id=item["owner_id"], title="Google Drive submission reviewed").count() == 1
    assert client.put(path, headers=artisan["headers"], json={"version":approved["version"],"url":"https://example.com"}).status_code == 422
    changed = client.put(path, headers=artisan["headers"], json={"version":approved["version"],"url":FOLDER}).json["item"]
    assert changed["kind"] == "folder" and changed["status"] == "pending" and changed["review_note"] is None
    assert profile()["external_portfolio"] == [] and review(client, admin, approved).status_code == 409
    rejected = review(client, admin, changed, "rejected").json["item"]
    assert profile()["external_portfolio"] == []
    assert client.delete(path, headers=artisan["headers"], json={"version":rejected["version"]}).status_code == 200
    assert DriveSubmission.query.count() == 0


def test_training_visibility_and_document_privacy(client, customer, admin):
    headers = customer["headers"]
    provider = TrainingProvider(name="College", institution_type="TVET", verification_status="approved")
    db.session.add(provider)
    db.session.flush()
    course = Course(provider_id=provider.id,title="Wiring basics",trade="Electrical",delivery_mode="onsite",published=True)
    db.session.add(course)
    db.session.commit()
    assert submit(client, headers, "course_material").status_code == 422
    assert submit(client, headers, "supporting_document", course_id=course.id).status_code == 422
    items = [submit(client, headers, purpose, **fields).json["item"] for purpose, fields in (
        ("course_material", {"course_id":course.id}), ("training_resource", {}), ("supporting_document", {}))]
    def visible():
        return client.get("/v1/training/drive-resources").json["items"]
    assert visible() == []
    for item in items:
        assert review(client, admin, item).status_code == 200
    assert {item["id"] for item in visible()} == {item["id"] for item in items[:2]}
    assert next(item for item in visible() if item["purpose"] == "course_material")["course_title"] == course.title
    course.published = False
    db.session.commit()
    assert [item["id"] for item in visible()] == [items[1]["id"]]
    course.published, provider.verification_status = True, "pending"
    db.session.commit()
    assert submit(client, headers, "course_material", course_id=course.id).status_code == 422
    assert [item["id"] for item in visible()] == [items[1]["id"]]


def test_private_evidence_purposes_are_excluded(client, artisan):
    for purpose in ("government_id","live_selfie","kyc","payout_name","trade_proof","booking_media",
                    "completion_evidence","dispute_evidence","workproof_evidence"):
        assert submit(client, artisan["headers"], purpose).status_code == 422
    assert DriveSubmission.query.count() == FileAsset.query.count() == 0
