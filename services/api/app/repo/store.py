"""Generic B2 object operations for the scene corpus.

The video-scene pipeline reads and writes many objects under the app's own
prefixes (source videos, scene clips, keyframes, embeddings, the FAISS index,
and per-video metadata JSON). All of it goes through the S3-compatible API via
the single cached, custom-user-agent client owned by ``b2_client`` — boto3 stays
confined to this ``repo/`` layer.
"""

from __future__ import annotations

import io
import json
from urllib.parse import quote

from botocore.exceptions import BotoCoreError, ClientError

from app.config import settings
from app.repo.b2_client import get_s3_client
from app.repo.list_cache import invalidate as _invalidate_list_cache


def _bucket() -> str:
    return settings.b2_bucket_name


def put_bytes(key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
    """Upload raw bytes to ``key``. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        client.put_object(
            Bucket=_bucket(), Key=key, Body=io.BytesIO(data), ContentType=content_type
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 put_object failed for '{key}': {e}") from e
    # The new object must show up in the full-bucket /files listing too.
    _invalidate_list_cache()


def get_bytes(key: str) -> bytes:
    """Download an object's full body. Raises RuntimeError on failure."""
    client = get_s3_client()
    try:
        response = client.get_object(Bucket=_bucket(), Key=key)
        return response["Body"].read()
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 get_object failed for '{key}': {e}") from e


def object_exists(key: str) -> bool:
    """True if the object exists (head_object). Raises RuntimeError on non-404 errors."""
    client = get_s3_client()
    try:
        client.head_object(Bucket=_bucket(), Key=key)
        return True
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code", "")
        if code in ("404", "NoSuchKey", "NotFound"):
            return False
        raise RuntimeError(f"B2 head_object failed for '{key}': {e}") from e


def list_prefix(prefix: str) -> list[dict]:
    """Every object under ``prefix`` as ``{key, size, last_modified}`` dicts.

    Paginates fully. Raises RuntimeError on failure.
    """
    client = get_s3_client()
    out: list[dict] = []
    kwargs: dict = {"Bucket": _bucket(), "Prefix": prefix, "MaxKeys": 1000}
    try:
        while True:
            response = client.list_objects_v2(**kwargs)
            for obj in response.get("Contents", []):
                out.append(
                    {
                        "key": obj["Key"],
                        "size": obj["Size"],
                        "last_modified": obj["LastModified"],
                    }
                )
            if not response.get("IsTruncated"):
                break
            kwargs["ContinuationToken"] = response["NextContinuationToken"]
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 list failed for '{prefix}': {e}") from e
    return out


def read_json(key: str) -> dict:
    """Read and parse a JSON object. Raises RuntimeError on S3/parse failure."""
    raw = get_bytes(key)
    try:
        return json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as e:
        raise RuntimeError(f"Invalid JSON at '{key}': {e}") from e


def write_json(key: str, obj: dict) -> None:
    """Serialize ``obj`` and upload it as ``application/json``."""
    data = json.dumps(obj, separators=(",", ":"), sort_keys=True).encode("utf-8")
    put_bytes(key, data, content_type="application/json")


def delete_prefix(prefix: str) -> int:
    """Delete every object under ``prefix``. Returns the count deleted.

    SAFETY: refuses an empty prefix so a bug can never wipe the whole bucket.
    Video deletes only ever pass a concrete, video-scoped prefix.
    """
    if not prefix or not prefix.strip():
        raise ValueError("delete_prefix refuses an empty prefix")
    client = get_s3_client()
    objects = [{"Key": item["key"]} for item in list_prefix(prefix)]
    if not objects:
        return 0
    deleted = 0
    try:
        # delete_objects caps at 1000 keys per request.
        for start in range(0, len(objects), 1000):
            batch = objects[start : start + 1000]
            client.delete_objects(Bucket=_bucket(), Delete={"Objects": batch})
            deleted += len(batch)
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 delete_objects failed for '{prefix}': {e}") from e
    _invalidate_list_cache()
    return deleted


def presign_get(key: str, expires_in: int = 3600) -> str:
    """Presigned GET URL for streaming a keyframe/clip to the browser."""
    client = get_s3_client()
    try:
        return client.generate_presigned_url(
            "get_object",
            Params={"Bucket": _bucket(), "Key": key},
            ExpiresIn=expires_in,
        )
    except (ClientError, BotoCoreError) as e:
        raise RuntimeError(f"B2 presign failed for '{key}': {e}") from e


def public_url(key: str) -> str | None:
    """Public URL for an object, or None when no public base is configured."""
    if not settings.b2_public_url_base:
        return None
    return f"{settings.b2_public_url_base}/{quote(key, safe='/')}"
