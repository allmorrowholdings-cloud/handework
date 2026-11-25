from io import BytesIO

import pytest

from handework.extensions import db
from handework.models import ArtisanProfile, FileAsset, User, Verification
from handework.services import storage


PNG = (b"\x89PNG\r\n\x1a\n" + b"\x00" * 20)


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.deleted = []
        self.fail_put = False

    def put_object(self, **kwargs):
        if self.fail_put:
            raise RuntimeError("provider write failed")
        self.objects[(kwargs["Bucket"], kwargs["Key"])] = kwargs

    def generate_presigned_url(self, operation, Params, ExpiresIn):
        return f"https://signed.invalid/{Params['Bucket']}/{Params['Key']}?expires={ExpiresIn}"

    def delete_object(self, **kwargs):
        self.deleted.append((kwargs["Bucket"], kwargs["Key"]))
        self.objects.pop((kwargs["Bucket"], kwargs["Key"]), None)


@pytest.fixture
def s3(monkeypatch):
    for key, value in {
        "STORAGE_MODE": "s3",
        "AWS_ACCESS_KEY_ID": "test-access-key",
        "AWS_SECRET_ACCESS_KEY": "test-secret-key",
        "AWS_REGION": "us-east-1",
        "S3_ENDPOINT_URL": "https://storage.example.test/storage/v1/s3",
        "S3_PRIVATE_BUCKET": "handework-private",
        "S3_MEDIA_BUCKET": "handework-media",
        "S3_EVIDENCE_BUCKET": "handework-evidence",
    }.items():
        monkeypatch.setenv(key, value)
    client = FakeS3()
    monkeypatch.setattr(storage, "s3_client", lambda: client)
    return client


def test_s3_client_uses_supabase_endpoint_and_path_style(monkeypatch):
    captured = {}
    monkeypatch.setenv("STORAGE_MODE", "s3")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("AWS_REGION", "eu-west-1")
    monkeypatch.setenv("S3_ENDPOINT_URL", "https://project.supabase.co/storage/v1/s3/")
    monkeypatch.setattr(storage.boto3, "client", lambda service, **kwargs: captured.update(service=service, **kwargs) or object())
    storage.s3_client()
    assert captured["service"] == "s3"
    assert captured["endpoint_url"] == "https://project.supabase.co/storage/v1/s3"
    assert captured["region_name"] == "eu-west-1"
    assert captured["config"].s3["addressing_style"] == "path"


def test_upload_records_metadata_signed_download_replace_and_delete(client, app, artisan, customer, s3):
    response = client.post("/v1/uploads", data={"purpose": "profile_picture", "file": (BytesIO(PNG), "avatar.png", "image/png")}, headers=artisan["headers"])
    assert response.status_code == 201, response.get_json()
    asset_id = response.get_json()["id"]
    with app.app_context():
        asset = db.session.get(FileAsset, asset_id)
        profile = db.session.query(ArtisanProfile).filter_by(user_id=artisan["user"]["id"]).one()
        assert asset.owner_id == artisan["user"]["id"]
        assert asset.storage_bucket == "handework-media"
        assert asset.size_bytes == len(PNG)
        assert len(asset.sha256) == 64
        assert profile.avatar_file_id == asset_id
        old_key = (asset.storage_bucket, asset.storage_key)
    signed = client.get(f"/v1/files/{asset_id}/download", headers=artisan["headers"])
    assert signed.status_code == 200 and signed.get_json()["expires_in"] == 300
    assert signed.get_json()["url"].startswith("https://signed.invalid/handework-media/")
    denied = client.get(f"/v1/files/{asset_id}/download", headers=customer["headers"])
    assert denied.status_code == 404

    replaced = client.put(f"/v1/files/{asset_id}", data={"file": (BytesIO(PNG + b"replacement"), "new.png", "image/png")}, headers=artisan["headers"])
    assert replaced.status_code == 200, replaced.get_json()
    replacement_id = replaced.get_json()["id"]
    with app.app_context():
        old = db.session.get(FileAsset, asset_id)
        new = db.session.get(FileAsset, replacement_id)
        profile = db.session.query(ArtisanProfile).filter_by(user_id=artisan["user"]["id"]).one()
        assert old.deleted_at is not None and new.replaces_asset_id == old.id
        assert profile.avatar_file_id == replacement_id
    assert old_key in s3.deleted
    deleted = client.delete(f"/v1/files/{replacement_id}", headers=artisan["headers"])
    assert deleted.status_code == 200
    with app.app_context():
        assert db.session.get(FileAsset, replacement_id).deleted_at is not None


def test_verification_document_uses_private_bucket_and_is_not_owner_listed(client, app, artisan, customer, s3):
    response = client.post("/v1/artisans/me/verifications", data={"kind": "government_id", "file": (BytesIO(PNG), "ghana-card.png", "image/png")}, headers=artisan["headers"])
    assert response.status_code == 201, response.get_json()
    with app.app_context():
        verification = Verification.query.filter_by(artisan_id=ArtisanProfile.query.filter_by(user_id=artisan["user"]["id"]).one().id, kind="government_id").one()
        asset = db.session.get(FileAsset, verification.file_asset_id)
        asset_id=asset.id
        assert verification.file_url == asset.url
        assert asset.storage_bucket == "handework-private"
        assert asset.is_private is True
    own = client.get(f"/v1/files/{asset_id}/download", headers=artisan["headers"])
    assert own.status_code == 200
    signed = client.get(f"/v1/admin/verifications", headers=artisan["headers"])
    assert signed.status_code == 403
    unrelated=client.get(f"/v1/files/{asset_id}/download",headers=customer["headers"])
    assert unrelated.status_code==404


def test_expiry_size_upload_cleanup_and_replacement_failure(client, app, artisan, customer, s3, monkeypatch):
    first = client.post("/v1/uploads", data={"purpose":"profile_picture","file":(BytesIO(PNG),"avatar.png","image/png")}, headers=artisan["headers"])
    assert first.status_code == 201
    asset_id = first.get_json()["id"]
    with app.app_context():
        original=db.session.get(FileAsset,asset_id)
        old_url, old_key = original.url, (original.storage_bucket,original.storage_key)
    url=client.get(f"/v1/files/{asset_id}/download",headers=artisan["headers"]).get_json()["url"]
    assert "expires=300" in url
    assert "expires=900" in storage.private_download_url(old_url,900)
    large=BytesIO(PNG + b"x" * (storage.MAX_FILE_BYTES + 1))
    too_large=client.post("/v1/uploads",data={"purpose":"profile_picture","file":(large,"large.png","image/png")},headers=artisan["headers"])
    assert too_large.status_code==413

    s3.fail_put=True
    failed_replace=client.put(f"/v1/files/{asset_id}",data={"file":(BytesIO(PNG),"new.png","image/png")},headers=artisan["headers"])
    assert failed_replace.status_code==503
    s3.fail_put=False
    with app.app_context():
        original=db.session.get(FileAsset,asset_id)
        assert original.deleted_at is None and (old_key in s3.objects)
        assert FileAsset.query.filter_by(owner_id=artisan["user"]["id"],purpose="profile_picture").count()==1

    session=db.session();original_commit=session.commit
    def fail_replace_commit(): raise RuntimeError("disposable database replacement failure")
    monkeypatch.setattr(session,"commit",fail_replace_commit)
    failed_db_replace=client.put(f"/v1/files/{asset_id}",data={"file":(BytesIO(PNG),"replacement.png","image/png")},headers=artisan["headers"])
    monkeypatch.setattr(session,"commit",original_commit)
    assert failed_db_replace.status_code==503
    with app.app_context():
        original=db.session.get(FileAsset,asset_id)
        assert original.deleted_at is None and FileAsset.query.filter_by(owner_id=artisan["user"]["id"],purpose="profile_picture").count()==1
    assert old_key in s3.objects

    session=db.session()
    original_commit=session.commit
    def fail_commit(): raise RuntimeError("disposable database write failed")
    monkeypatch.setattr(session,"commit",fail_commit)
    failed_upload=client.post("/v1/uploads",data={"purpose":"profile_picture","file":(BytesIO(PNG),"orphan.png","image/png")},headers=artisan["headers"])
    monkeypatch.setattr(session,"commit",original_commit)
    assert failed_upload.status_code==503
    with app.app_context():
        assert FileAsset.query.filter_by(owner_id=artisan["user"]["id"],purpose="profile_picture").count()==1
    assert len(s3.objects)==1 and len(s3.deleted)==2


def test_public_portfolio_and_shop_media_use_signed_private_objects(client, app, artisan, s3, monkeypatch):
    avatar=client.post("/v1/uploads",data={"purpose":"profile_picture","file":(BytesIO(PNG),"avatar.png","image/png")},headers=artisan["headers"])
    assert avatar.status_code==201
    portfolio=client.post("/v1/artisans/me/portfolio",data={"title":"Sink repair","service":"Plumbing","file":(BytesIO(PNG),"work.png","image/png")},headers=artisan["headers"])
    assert portfolio.status_code==201,portfolio.get_json()
    proof=client.post("/v1/workproof/me",data={"title":"Tap installation","verifier_name":"Ama Client","verifier_contact":"ama@example.test","file":(BytesIO(PNG),"proof.png","image/png")},headers=artisan["headers"])
    assert proof.status_code==201,proof.get_json()
    personal=client.get("/v1/workproof/me",headers=artisan["headers"]).get_json()["workproof"]["submissions"][0]
    assert personal["evidence_url"].startswith("https://signed.invalid/handework-evidence/")
    with app.app_context():
        from handework.models import PortfolioItem, Role
        item=PortfolioItem.query.get(portfolio.get_json()["item"]["id"]);item.moderation_status="approved";db.session.commit()
        account=db.session.get(User,artisan["user"]["id"]);account.role=Role.ADMIN;db.session.commit()
    public=client.get(f"/v1/artisans/{artisan['profile_id']}")
    assert public.status_code==200
    media_url=public.get_json()["portfolio"][0]["media_url"]
    assert media_url.startswith("https://signed.invalid/") and not media_url.startswith("s3://")
    avatar_url=public.get_json()["artisan"]["avatar_url"]
    assert avatar_url.startswith("https://signed.invalid/") and "s3://" not in avatar_url
    monkeypatch.setenv("SHOP_PUBLISHED_PRODUCT_IDS","plumb-kit")
    uploaded=client.put("/v1/admin/shop-products/plumb-kit/image",data={"file":(BytesIO(PNG),"kit.png","image/png")},headers=artisan["headers"])
    assert uploaded.status_code==201,uploaded.get_json()
    product=client.get("/v1/shop/products").get_json()["items"][0]
    assert product["image"].startswith("https://signed.invalid/") and "handework-media" in product["image"]


def test_rejects_mime_spoof_and_fails_closed_without_s3(client, artisan, monkeypatch):
    spoofed = client.post("/v1/uploads", data={"purpose": "profile_picture", "file": (BytesIO(b"not a png"), "bad.png", "image/png")}, headers=artisan["headers"])
    assert spoofed.status_code == 422
    monkeypatch.delenv("STORAGE_MODE", raising=False)
    monkeypatch.setattr(storage, "s3_client", lambda: pytest.fail("Must not attempt S3 without explicit storage mode"))
    with pytest.raises(RuntimeError, match="Persistent storage is unavailable"):
        storage.upload_file(type("Upload", (), {"mimetype":"image/png","stream":BytesIO(PNG),"filename":"test.png"})(), artisan["user"]["id"], "profile_picture")


def test_local_storage_is_never_allowed_in_production(app, artisan, monkeypatch):
    monkeypatch.setenv("APP_ENV","production");monkeypatch.setenv("FLASK_ENV","production");monkeypatch.setenv("STORAGE_MODE","local")
    with app.app_context():
        app.config["TESTING"]=False
        with pytest.raises(RuntimeError,match="Persistent storage is unavailable"):
            storage.upload_file(type("Upload",(),{"mimetype":"image/png","stream":BytesIO(PNG),"filename":"test.png"})(),artisan["user"]["id"],"profile_picture")


def test_booking_and_dispute_evidence_lifecycle(client, customer, artisan, s3):
    from handework.models import Booking, BookingStatus
    from test_payments import payable_booking

    booking_id = payable_booking(client, customer, artisan)
    booking = db.session.get(Booking, booking_id)
    booking.status = BookingStatus.IN_PROGRESS
    db.session.commit()

    def upload(purpose, account):
        return client.post("/v1/uploads", headers=account["headers"], data={
            "purpose": purpose, "booking_id": booking_id,
            "file": (BytesIO(PNG), "evidence.png", "image/png"),
        })

    assert upload("dispute_evidence", customer).status_code == 409
    assert upload("completion_evidence", customer).status_code == 403
    attachment = upload("booking_media", customer)
    assert attachment.status_code == 201
    attachment_id = attachment.json["id"]
    evidence = upload("completion_evidence", artisan)
    assert evidence.status_code == 201
    assert db.session.get(FileAsset, evidence.json["id"]).storage_bucket == "handework-evidence"
    assert client.delete(f"/v1/files/{attachment_id}", headers=customer["headers"]).status_code == 200
    record = client.get(f"/v1/bookings/{booking_id}", headers=customer["headers"])
    assert [item["id"] for item in record.json["attachments"]] == [evidence.json["id"]]

    dispute = client.post("/v1/disputes", headers=customer["headers"], json={
        "booking_id": booking_id, "description": "Work needs review",
    })
    assert dispute.status_code == 201
    response = upload("dispute_evidence", customer)
    assert response.status_code == 201
    path = "/v1/files/" + response.json["id"]
    assert client.post("/v1/disputes/" + dispute.json["id"] + "/responses",
                       headers=customer["headers"], json={"message": "Photo", "asset_id": response.json["id"]}).status_code == 201
    assert client.get(path + "/download", headers=artisan["headers"]).json["url"].startswith(
        "https://signed.invalid/handework-evidence/")
    assert client.put(path, headers=customer["headers"], data={
        "file": (BytesIO(PNG), "new.png", "image/png"),
    }).status_code == 409
    assert client.delete(path, headers=customer["headers"]).status_code == 409


def test_local_upload_and_delete(app, client, artisan, tmp_path, monkeypatch):
    monkeypatch.setenv("STORAGE_MODE", "local")
    monkeypatch.setenv("LOCAL_UPLOAD_DIR", str(tmp_path))
    response = client.post("/v1/uploads", headers=artisan["headers"], data={
        "purpose": "profile_picture", "file": (BytesIO(PNG), "avatar.png", "image/png"),
    })
    assert response.status_code == 201
    asset = db.session.get(FileAsset, response.json["id"])
    destination = tmp_path / asset.storage_key
    assert destination.read_bytes() == PNG
    assert client.delete("/v1/files/" + asset.id, headers=artisan["headers"]).status_code == 200
    assert not destination.exists()
