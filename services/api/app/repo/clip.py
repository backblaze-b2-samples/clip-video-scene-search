"""CLIP / OpenCLIP keyframe + text embedding.

This is the ONLY module that imports torch / open_clip. Every import is lazy and
happens inside a function, so importing the app (and running the structural /
contract tests) never pulls the multi-GB native stack and no model weights are
downloaded at build time — the weights download on the first real embed call
(the "Build scene index" action), never during setup or import.

Device is auto-detected CUDA -> Apple MPS -> CPU with CPU as the safe default;
a GPU is never hard-required (parent build directive + api-provider-selection).
"""

from __future__ import annotations

import io
import threading
from typing import TYPE_CHECKING

from app.config import settings

if TYPE_CHECKING:  # import only for type hints; never at runtime
    import numpy as np

_lock = threading.Lock()
_model_cache: dict | None = None


def select_device(override: str = "") -> str:
    """Pick the compute device: explicit override -> CUDA -> MPS -> CPU."""
    import torch

    if override:
        return override
    if torch.cuda.is_available():
        return "cuda"
    mps = getattr(torch.backends, "mps", None)
    if mps is not None and mps.is_available():
        return "mps"
    return "cpu"


def _parse_model_spec(spec: str) -> tuple[str, str]:
    """Split "ViT-B-32/laion2b_s34b_b79k" into (architecture, pretrained_tag)."""
    if "/" in spec:
        arch, pretrained = spec.split("/", 1)
        return arch, pretrained
    return spec, ""


def _load() -> dict:
    """Load (once) and cache the model, preprocess transform, and tokenizer.

    The model is the single GLOBAL ``settings.clip_model`` — there is no
    per-video override. All keyframe and query vectors therefore share one
    dimensionality, which is what lets them live in the one shared FAISS index.
    """
    global _model_cache
    with _lock:
        if _model_cache is not None:
            return _model_cache

        import open_clip
        import torch

        arch, pretrained = _parse_model_spec(settings.clip_model)
        device = select_device(settings.clip_device)
        model, _, preprocess = open_clip.create_model_and_transforms(
            arch, pretrained=pretrained, device=device
        )
        model.eval()
        tokenizer = open_clip.get_tokenizer(arch)
        _model_cache = {
            "model": model,
            "preprocess": preprocess,
            "tokenizer": tokenizer,
            "device": device,
            "torch": torch,
        }
        return _model_cache


def active_device() -> str:
    """The device the model is (or would be) loaded on — for diagnostics."""
    if _model_cache is not None:
        return _model_cache["device"]
    return select_device(settings.clip_device)


def _normalize(vec: np.ndarray) -> np.ndarray:
    import numpy as np

    norm = np.linalg.norm(vec)
    if norm == 0:
        return vec.astype("float32")
    return (vec / norm).astype("float32")


def embed_image(data: bytes) -> np.ndarray:
    """Embed image bytes into an L2-normalized float32 vector."""
    import numpy as np
    from PIL import Image

    ctx = _load()
    torch = ctx["torch"]
    image = Image.open(io.BytesIO(data)).convert("RGB")
    tensor = ctx["preprocess"](image).unsqueeze(0).to(ctx["device"])
    with torch.no_grad():
        features = ctx["model"].encode_image(tensor)
    vec = features.cpu().numpy()[0].astype("float32")
    return _normalize(np.asarray(vec))


def embed_text(text: str) -> np.ndarray:
    """Embed a text query into an L2-normalized float32 vector."""
    import numpy as np

    ctx = _load()
    torch = ctx["torch"]
    tokens = ctx["tokenizer"]([text]).to(ctx["device"])
    with torch.no_grad():
        features = ctx["model"].encode_text(tokens)
    vec = features.cpu().numpy()[0].astype("float32")
    return _normalize(np.asarray(vec))
