"""Private object storage backed by Supabase's S3-compatible endpoint."""
from __future__ import annotations

import hashlib
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from botocore.config import Config as BotoConfig
from flask import current_app, has_app_context
from itsdangerous import URLSafeTimedSerializer

ALLOWED = {
    "image/jpeg": ("jpg", (b"\xff\xd8\xff",)),
    "image/png": ("png", (b"\x89PNG\r\n\x1a\n",)),
    "image/webp": ("webp", (b"RIFF",)),
    "video/mp4": ("mp4", (b"",)),
    "application/pdf": ("pdf", (b"%PDF-",)),
}
MAX_FILE_BYTES = 15 * 1024 * 1024
PRIVATE_PURPOSES = {"verification", "government_id", "live_selfie", "trade_certificate", "trade_proof"}
EVIDENCE_PURPOSES = {"completion_evidence", "dispute_evidence", "workproof_evidence"}


@dataclass(frozen=True)
class StoredObject:
    bucket: str
    key: str
    url: str
    mime_type: str
    size_bytes: int
    sha256: str
    filename: str
    is_private: bool = True


def local_signer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="private-media")


def _mode() -> str:
    return os.getenv("STORAGE_MODE", "").strip().lower()


def local_storage_allowed(app=None) -> bool:
    testing = app.config.get("TESTING", False) if app is not None else (current_app.config.get("TESTING", False) if has_app_context() else False)
    return bool(testing or os.getenv("APP_ENV", "").lower() == "development" or os.getenv("FLASK_ENV", "").lower() == "development")


def _bucket_for(purpose: str) -> str:
    if purpose in PRIVATE_PURPOSES:
        name, default = "S3_PRIVATE_BUCKET", "handework-private"
    elif purpose in EVIDENCE_PURPOSES:
        name, default = "S3_EVIDENCE_BUCKET", "handework-evidence"
    else:
        name, default = "S3_MEDIA_BUCKET", "handework-media"
    return (os.getenv(name) or default).strip()


def s3_client():
    if _mode() != "s3":
        raise RuntimeError("S3 storage is not enabled (set STORAGE_MODE=s3)")
    missing = [key for key in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_REGION", "S3_ENDPOINT_URL") if not os.getenv(key)]
    if missing:
        raise RuntimeError("S3 storage is not configured: " + ", ".join(missing))
    return boto3.client(
        "s3",
        endpoint_url=os.environ["S3_ENDPOINT_URL"].rstrip("/"),
        region_name=os.environ["AWS_REGION"],
        aws_access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
        config=BotoConfig(s3={"addressing_style": "path"}, signature_version="s3v4"),
    )


def _validate_content(file) -> tuple[bytes, str]:
    declared = (file.mimetype or "").lower().split(";", 1)[0].strip()
    if declared not in ALLOWED:
        raise ValueError("Unsupported file type")
    raw = file.stream.read(MAX_FILE_BYTES + 1)
    if not raw:
        raise ValueError("Choose a non-empty file")
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("File exceeds the 15 MB upload limit")
    if declared == "image/webp":
        valid = len(raw) >= 12 and raw[:4] == b"RIFF" and raw[8:12] == b"WEBP"
    elif declared == "video/mp4":
        valid = len(raw) >= 12 and raw[4:8] == b"ftyp"
    else:
        valid = raw.startswith(ALLOWED[declared][1][0])
    if not valid:
        raise ValueError("File contents do not match the declared MIME type")
    return raw, declared


def upload_file(file, owner_id, purpose, private=True) -> StoredObject:
    if not file:
        raise ValueError("Choose a file to upload")
    raw, mime_type = _validate_content(file)
    if purpose in {"profile_picture", "shop_image"} and not mime_type.startswith("image/"):
        raise ValueError("Choose an image file")
    if purpose == "portfolio" and mime_type == "application/pdf":
        raise ValueError("Choose a photo or video")
    key = f"{purpose}/{owner_id}/{uuid.uuid4()}.{ALLOWED[mime_type][0]}"
    if _mode() == "local" and local_storage_allowed():
        root = Path(os.getenv("LOCAL_UPLOAD_DIR") or Path(__file__).resolve().parents[2] / "uploads")
        destination = root / key
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        bucket, url = "local", "private-local:" + key
    elif _mode() == "s3":
        bucket = _bucket_for(purpose)
        url = f"s3://{bucket}/{key}"
        try:
            s3_client().put_object(Bucket=bucket, Key=key, Body=raw, ContentType=mime_type, CacheControl="private, no-store")
        except (BotoCoreError, ClientError) as error:
            raise RuntimeError("File storage is temporarily unavailable") from error
    else:
        raise RuntimeError("Persistent storage is unavailable; configure STORAGE_MODE=s3")
    return StoredObject(bucket, key, url, mime_type, len(raw), hashlib.sha256(raw).hexdigest(), (file.filename or "upload")[:255])


def signed_url(value: str, expires: int = 300) -> str:
    if not value:
        return value
    if value.startswith("private-local:"):
        if _mode() != "local" or not local_storage_allowed():
            raise RuntimeError("Local file links are only available in isolated local tests")
        token = local_signer().dumps(value.removeprefix("private-local:"))
        base = os.getenv("PUBLIC_API_URL", "http://localhost:5000").rstrip("/")
        return f"{base}/v1/private-download/{token}"
    if not value.startswith("s3://"):
        return value
    bucket, key = value[5:].split("/", 1)
    return s3_client().generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=min(max(int(expires), 1), 900))


def private_download_url(value: str, expires: int = 300) -> str:
    """Compatibility name used by existing serializers; URLs are always short lived."""
    return signed_url(value, expires)


def delete_object(value: str) -> None:
    if not value:
        return
    if value.startswith("s3://"):
        bucket, key = value[5:].split("/", 1)
        s3_client().delete_object(Bucket=bucket, Key=key)
    elif value.startswith("private-local:"):
        if _mode() != "local" or not local_storage_allowed():
            raise RuntimeError("Local file deletion is disabled")
        (Path(os.getenv("LOCAL_UPLOAD_DIR") or Path(__file__).resolve().parents[2] / "uploads") / value.removeprefix("private-local:")).unlink(missing_ok=True)


def metadata_for(stored: StoredObject) -> dict:
    return {"url": stored.url, "storage_bucket": stored.bucket, "storage_key": stored.key,
            "original_filename": stored.filename, "size_bytes": stored.size_bytes,
            "sha256": stored.sha256, "is_private": stored.is_private, "mime_type": stored.mime_type}
