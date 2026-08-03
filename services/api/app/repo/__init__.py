import os

# torch and faiss each bundle their own OpenMP runtime; on macOS arm64 loading
# both aborts with "OMP: Error #15 ... multiple copies of the OpenMP runtime".
# Setting this BEFORE either native library loads is the documented workaround.
# The repo/ package is imported early (it owns the B2 client), so this runs
# before any lazy torch/faiss import in repo/clip.py / repo/faiss_index.py.
# faiss is additionally capped to one OpenMP thread there — the env var alone is
# not enough.
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

from app.repo.b2_client import (
    check_connectivity,
    delete_file,
    get_file_metadata,
    get_presigned_url,
    get_upload_stats,
    list_files,
    prewarm_listing,
    upload_file,
)
from app.repo.b2_object import get_object_bytes
from app.repo.counter import get_download_count, increment_download_count

__all__ = [
    "check_connectivity",
    "delete_file",
    "get_download_count",
    "get_file_metadata",
    "get_object_bytes",
    "get_presigned_url",
    "get_upload_stats",
    "increment_download_count",
    "list_files",
    "prewarm_listing",
    "upload_file",
]
