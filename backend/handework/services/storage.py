import os
import uuid
from pathlib import Path
import boto3
from flask import current_app
from itsdangerous import URLSafeTimedSerializer

ALLOWED = {"image/jpeg", "image/png", "image/webp", "video/mp4", "application/pdf"}


def local_signer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="private-media")


def _local_upload(file, owner_id, purpose, private):
    root = Path(os.getenv("LOCAL_UPLOAD_DIR") or Path(__file__).resolve().parents[2] / "uploads")
    extension = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp","video/mp4":"mp4","application/pdf":"pdf"}[file.mimetype]
    relative = Path(purpose) / str(owner_id) / f"{uuid.uuid4()}.{extension}"
    destination = root / relative
    destination.parent.mkdir(parents=True, exist_ok=True)
    file.save(destination)
    if private:
        return "private-local:" + relative.as_posix()
    base = os.getenv("PUBLIC_API_URL", "http://localhost:5000").rstrip("/")
    return f"{base}/v1/local-uploads/{relative.as_posix()}"


def upload_file(file, owner_id, purpose, private=False):
    if not file or file.mimetype not in ALLOWED:
        raise ValueError("Unsupported file type")
    bucket = os.getenv("S3_BUCKET")
    if not bucket:
        if os.getenv("FLASK_ENV") == "development" or os.getenv("STORAGE_MODE") == "local":
            return _local_upload(file, owner_id, purpose, private)
        raise RuntimeError("S3_BUCKET is not configured")
    extension = {"image/jpeg":"jpg","image/png":"png","image/webp":"webp","video/mp4":"mp4","application/pdf":"pdf"}[file.mimetype]
    key = f"{purpose}/{owner_id}/{uuid.uuid4()}.{extension}"
    client = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    client.upload_fileobj(file.stream, bucket, key, ExtraArgs={"ContentType": file.mimetype, "ServerSideEncryption": "AES256"})
    if private:
        return f"s3://{bucket}/{key}"
    base = os.getenv("S3_PUBLIC_BASE_URL", "").rstrip("/")
    return f"{base}/{key}" if base else client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=3600)


def private_download_url(value, expires=900):
    if value and value.startswith("private-local:"):
        token = local_signer().dumps(value.removeprefix("private-local:"))
        base = os.getenv("PUBLIC_API_URL", "http://localhost:5000").rstrip("/")
        return f"{base}/v1/private-download/{token}"
    if value and "/v1/local-uploads/" in value:
        relative = value.split("/v1/local-uploads/", 1)[1]
        if relative.split("/", 1)[0] in {"verification", "booking_media", "chat_media"}:
            return private_download_url("private-local:" + relative, expires)
    if not value or not value.startswith("s3://"):
        return value
    bucket, key = value[5:].split("/", 1)
    client = boto3.client("s3", region_name=os.getenv("AWS_REGION"))
    return client.generate_presigned_url("get_object", Params={"Bucket": bucket, "Key": key}, ExpiresIn=expires)
