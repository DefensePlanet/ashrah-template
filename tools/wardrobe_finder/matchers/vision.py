"""
Vision-based matching using a two-tier approach to compare product images
to listing thumbnails.

Tier 1 (Primary): Local CLIP embeddings via open_clip_torch.
  - Downloads images, generates CLIP embeddings, computes cosine similarity.
  - Fast, free, no API calls. Requires torch + open_clip_torch + PIL.

Tier 2 (Fallback): Codex Vision via Anthropic Claude API (Haiku 4.5).
  - Sends product image + batch of thumbnails in a single multimodal message.
  - Requires ANTHROPIC_API_KEY environment variable.

If neither tier is available, vision matching is skipped gracefully.
"""

import base64
import io
import json
import logging
import os
import re
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# Blend weights: text-based vs vision-based scoring
TEXT_WEIGHT = 0.6
VISION_WEIGHT = 0.4

# ---------------------------------------------------------------------------
# Lazy-loaded CLIP model cache (module-level, loaded once per session)
# ---------------------------------------------------------------------------

_clip_model = None
_clip_preprocess = None
_clip_tokenizer = None
_clip_available: Optional[bool] = None  # None = not yet checked


def _load_clip():
    """Lazy-load the CLIP model on first use. Returns True if available."""
    global _clip_model, _clip_preprocess, _clip_tokenizer, _clip_available

    if _clip_available is not None:
        return _clip_available

    try:
        import torch
        import open_clip

        model, _, preprocess = open_clip.create_model_and_transforms(
            "ViT-B-32", pretrained="laion2b_s34b_b79k"
        )
        tokenizer = open_clip.get_tokenizer("ViT-B-32")
        model.eval()

        _clip_model = model
        _clip_preprocess = preprocess
        _clip_tokenizer = tokenizer
        _clip_available = True
        logger.info("CLIP model loaded successfully (ViT-B-32)")
        return True
    except ImportError as e:
        logger.info(
            "CLIP not available (missing dependency: %s). "
            "Install with: pip install open_clip_torch torch",
            e,
        )
        _clip_available = False
        return False
    except Exception as e:
        logger.warning("CLIP model failed to load: %s", e)
        _clip_available = False
        return False


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_visual_matches(
    product_image_url: str,
    product_description: str,
    results: list,
    max_comparisons: int = 10,
) -> Dict[str, float]:
    """Score listing thumbnails against the product image using vision matching.

    Two-tier approach:
      1. CLIP local embeddings (fast, free, no API calls)
      2. Codex Vision / Anthropic Claude Haiku 4.5 (API fallback)

    Returns a dict mapping result URL -> vision similarity score (0.0-1.0).
    Only processes the top N results (by current text score) to limit work.
    Results without thumbnails are not included in the returned dict.

    Args:
        product_image_url: URL of the reference product image.
        product_description: Short text description (brand + model).
        results: List of SearchResult objects with text-based match_scores.
        max_comparisons: Max number of listing images to compare.

    Returns:
        Dict of {result_url: vision_score} where score is 0.0-1.0.
        Empty dict if vision matching is unavailable or fails.
    """
    if not product_image_url:
        logger.debug("No product image URL, skipping vision matching")
        return {}

    if not results:
        return {}

    # Download reference product image
    logger.info("Downloading product image for vision matching: %s", product_image_url[:80])
    product_b64 = _download_image_b64(product_image_url)
    if not product_b64:
        logger.warning("Failed to download product image from %s", product_image_url[:80])
        return {}
    logger.info("Product image downloaded (%d bytes encoded)", len(product_b64))

    # Select top N results that have thumbnails, sorted by current score
    candidates: List[Tuple[int, object]] = []
    for i, r in enumerate(results):
        if r.thumbnail:
            candidates.append((i, r))

    logger.info(
        "Vision candidates: %d of %d results have thumbnails",
        len(candidates), len(results),
    )

    # Sort by current text score descending
    candidates.sort(key=lambda x: x[1].match_score, reverse=True)
    candidates = candidates[:max_comparisons]

    if not candidates:
        logger.info("No results with thumbnails, skipping vision matching")
        return {}

    # Download thumbnails
    thumbnail_data: List[Tuple[int, str]] = []  # (original_index, b64)
    download_failures = 0
    for idx, r in candidates:
        b64 = _download_image_b64(r.thumbnail)
        if b64:
            thumbnail_data.append((idx, b64))
        else:
            download_failures += 1
            logger.debug("Failed to download thumbnail for result %d: %s", idx, r.thumbnail[:80])

    if download_failures > 0:
        logger.info(
            "Thumbnail downloads: %d succeeded, %d failed",
            len(thumbnail_data), download_failures,
        )

    if not thumbnail_data:
        logger.warning("All thumbnail downloads failed, skipping vision matching")
        return {}

    logger.info(
        "Vision matching: comparing %d thumbnails against product image",
        len(thumbnail_data),
    )

    # --- Tier 1: CLIP local embeddings ---
    thumbnail_b64s = [b64 for _, b64 in thumbnail_data]
    vision_scores = _score_with_clip(product_b64, thumbnail_b64s)

    if vision_scores is not None:
        logger.info("CLIP (Tier 1) produced %d scores", len(vision_scores))
    else:
        logger.info("CLIP (Tier 1) unavailable, trying Codex Vision (Tier 2)")

    # --- Tier 2: Codex Vision (Anthropic Claude) fallback ---
    if vision_scores is None:
        vision_scores = _score_with_codex(
            product_b64, thumbnail_b64s, product_description
        )
        if vision_scores is not None:
            logger.info("Codex Vision (Tier 2) produced %d scores", len(vision_scores))
        else:
            logger.warning("Codex Vision (Tier 2) also failed")

    if not vision_scores or len(vision_scores) != len(thumbnail_data):
        logger.warning(
            "Vision scoring returned %s scores for %d images — "
            "both CLIP and Codex tiers unavailable or failed. "
            "Install open_clip_torch for local vision: pip install open_clip_torch torch",
            len(vision_scores) if vision_scores else 0,
            len(thumbnail_data),
        )
        return {}

    # Build URL -> score dict (normalize 0-100 int to 0.0-1.0 float)
    url_scores: Dict[str, float] = {}
    for (orig_idx, _b64), vision_score in zip(thumbnail_data, vision_scores):
        r = results[orig_idx]
        normalized = max(0.0, min(1.0, vision_score / 100.0))
        url_scores[r.url] = normalized
        logger.debug(
            "Vision score for result %d: %d/100 (%.2f) — %s",
            orig_idx, vision_score, normalized, r.title[:40],
        )

    logger.info(
        "Vision matching complete: %d scores, avg=%.2f",
        len(url_scores),
        sum(url_scores.values()) / len(url_scores) if url_scores else 0,
    )

    return url_scores


# ---------------------------------------------------------------------------
# Tier 1: CLIP local embeddings
# ---------------------------------------------------------------------------


def _score_with_clip(
    product_b64: str,
    thumbnail_b64s: List[str],
) -> Optional[List[int]]:
    """Score thumbnails against the product image using local CLIP embeddings.

    Computes cosine similarity between the product image embedding and each
    thumbnail embedding. Converts the raw similarity (typically 0.0-1.0 range
    for similar images) to a 0-100 integer score.

    Args:
        product_b64: Base64-encoded product image.
        thumbnail_b64s: List of base64-encoded thumbnails.

    Returns:
        List of integer scores (0-100), or None if CLIP is unavailable.
    """
    if not _load_clip():
        return None

    try:
        import torch
        from PIL import Image

        logger.info("Using CLIP local embeddings (Tier 1)")

        # Decode base64 images to PIL
        product_img = _b64_to_pil(product_b64)
        if product_img is None:
            logger.warning("Failed to decode product image for CLIP")
            return None

        thumbnail_imgs = []
        valid_indices = []
        for i, tb64 in enumerate(thumbnail_b64s):
            img = _b64_to_pil(tb64)
            if img is not None:
                thumbnail_imgs.append(img)
                valid_indices.append(i)

        if not thumbnail_imgs:
            logger.warning("No thumbnails decoded successfully for CLIP")
            return None

        # Preprocess images
        product_tensor = _clip_preprocess(product_img).unsqueeze(0)
        thumb_tensors = torch.stack(
            [_clip_preprocess(img) for img in thumbnail_imgs]
        )

        # Generate embeddings (no gradient needed)
        with torch.no_grad():
            product_features = _clip_model.encode_image(product_tensor)
            thumb_features = _clip_model.encode_image(thumb_tensors)

            # Normalize for cosine similarity
            product_features = product_features / product_features.norm(
                dim=-1, keepdim=True
            )
            thumb_features = thumb_features / thumb_features.norm(
                dim=-1, keepdim=True
            )

            # Cosine similarity: (1, D) @ (D, N) -> (1, N)
            similarities = (product_features @ thumb_features.T).squeeze(0)

        # Convert similarities to 0-100 scores.
        # CLIP image-to-image cosine similarity typically ranges:
        #   ~0.40 (unrelated) to ~0.85+ (same product).
        # We rescale [0.40, 0.85] -> [0, 100], clamped.
        # Widened from [0.50, 0.90] to reduce false zeros on
        # legitimate product matches.
        LOW_SIM = 0.40
        HIGH_SIM = 0.85
        scores = [0] * len(thumbnail_b64s)
        for i, vi in enumerate(valid_indices):
            raw_sim = similarities[i].item()
            scaled = (raw_sim - LOW_SIM) / (HIGH_SIM - LOW_SIM) * 100.0
            scores[vi] = max(0, min(100, round(scaled)))

        logger.info(
            "CLIP scores: %s (raw sims: %s)",
            [scores[vi] for vi in valid_indices],
            [f"{similarities[i].item():.3f}" for i in range(len(valid_indices))],
        )

        return scores

    except Exception as e:
        logger.warning("CLIP scoring failed, falling through to Tier 2: %s", e)
        import traceback
        logger.debug("CLIP traceback:\n%s", traceback.format_exc())
        return None


def _b64_to_pil(b64_str: str):
    """Decode a base64 string to a PIL Image. Returns None on failure."""
    try:
        from PIL import Image
        raw = base64.b64decode(b64_str)
        return Image.open(io.BytesIO(raw)).convert("RGB")
    except Exception as e:
        logger.debug("Failed to decode base64 image to PIL: %s", e)
        return None


# ---------------------------------------------------------------------------
# Tier 2: Codex Vision (Anthropic Claude Haiku 4.5)
# ---------------------------------------------------------------------------


def _score_with_codex(
    product_b64: str,
    thumbnail_b64s: List[str],
    product_desc: str,
) -> Optional[List[int]]:
    """Score thumbnails using Anthropic Claude Haiku 4.5 vision.

    Sends the product image + all thumbnails in a single multimodal message
    and asks for a JSON array of 0-100 similarity scores.

    Args:
        product_b64: Base64-encoded product image.
        thumbnail_b64s: List of base64-encoded thumbnails.
        product_desc: Text description for context (e.g. "Nike Air Force 1").

    Returns:
        List of integer scores (0-100), or None if unavailable.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.debug("ANTHROPIC_API_KEY not set, skipping Codex Vision fallback")
        return None

    # Try the Anthropic SDK first, then fall back to raw HTTP
    scores = _codex_via_sdk(product_b64, thumbnail_b64s, product_desc, api_key)
    if scores is not None:
        return scores

    return _codex_via_http(product_b64, thumbnail_b64s, product_desc, api_key)


def _codex_via_sdk(
    product_b64: str,
    thumbnail_b64s: List[str],
    product_desc: str,
    api_key: str,
) -> Optional[List[int]]:
    """Call Anthropic Claude via the Python SDK."""
    try:
        import anthropic
    except ImportError:
        logger.debug("anthropic SDK not installed, trying raw HTTP fallback")
        return None

    logger.info("Using Codex Vision fallback — Anthropic Haiku 4.5 (Tier 2, SDK)")

    try:
        client = anthropic.Anthropic(api_key=api_key)

        # Build content blocks: text prompt, product image, then thumbnails
        content = [
            {
                "type": "text",
                "text": (
                    f"I'm comparing a reference product image against secondhand "
                    f"marketplace listing photos.\n"
                    f"Reference product: {product_desc}\n\n"
                    f"For each numbered listing image, rate 0-100 how confident you "
                    f"are it shows the SAME product as the reference image.\n"
                    f"Consider: same brand, same style/model, same general appearance. "
                    f"Color variants are OK (score 70+). "
                    f"Different products from the same brand should score below 30.\n\n"
                    f"Return ONLY a JSON array of integer scores, one per listing. "
                    f"Example: [85, 45, 92, 10, 73]"
                ),
            },
            {
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": product_b64,
                },
            },
            {
                "type": "text",
                "text": "Reference image above. Now the listing images:",
            },
        ]

        for i, thumb_b64 in enumerate(thumbnail_b64s):
            content.append({
                "type": "text",
                "text": f"Listing {i + 1}:",
            })
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": thumb_b64,
                },
            })

        response = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": content}],
        )

        response_text = response.content[0].text
        return _parse_scores(response_text, len(thumbnail_b64s))

    except Exception as e:
        logger.warning("Codex Vision SDK call failed: %s", e)
        return None


def _codex_via_http(
    product_b64: str,
    thumbnail_b64s: List[str],
    product_desc: str,
    api_key: str,
) -> Optional[List[int]]:
    """Call Anthropic Claude via raw HTTP (no SDK needed)."""
    logger.info("Using Codex Vision fallback — Anthropic Haiku 4.5 (Tier 2, HTTP)")

    url = "https://api.anthropic.com/v1/messages"
    headers = {
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    # Build content blocks
    content = [
        {
            "type": "text",
            "text": (
                f"I'm comparing a reference product image against secondhand "
                f"marketplace listing photos.\n"
                f"Reference product: {product_desc}\n\n"
                f"For each numbered listing image, rate 0-100 how confident you "
                f"are it shows the SAME product as the reference image.\n"
                f"Consider: same brand, same style/model, same general appearance. "
                f"Color variants are OK (score 70+). "
                f"Different products from the same brand should score below 30.\n\n"
                f"Return ONLY a JSON array of integer scores, one per listing. "
                f"Example: [85, 45, 92, 10, 73]"
            ),
        },
        {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": product_b64,
            },
        },
        {
            "type": "text",
            "text": "Reference image above. Now the listing images:",
        },
    ]

    for i, thumb_b64 in enumerate(thumbnail_b64s):
        content.append({"type": "text", "text": f"Listing {i + 1}:"})
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": "image/jpeg",
                "data": thumb_b64,
            },
        })

    payload = {
        "model": "claude-haiku-4-5-20251001",
        "max_tokens": 200,
        "messages": [{"role": "user", "content": content}],
    }

    # Try requests first
    try:
        import requests as req_lib
        resp = req_lib.post(url, json=payload, headers=headers, timeout=30)
        if resp.status_code == 200:
            data = resp.json()
            try:
                response_text = data["content"][0]["text"]
                return _parse_scores(response_text, len(thumbnail_b64s))
            except (KeyError, IndexError, TypeError):
                logger.warning("Unexpected Codex Vision response: %s", data)
                return None
        logger.warning(
            "Codex Vision API returned status %d: %s",
            resp.status_code,
            resp.text[:200],
        )
        return None
    except ImportError:
        pass
    except Exception as e:
        logger.warning("Codex Vision API call failed (requests): %s", e)
        return None

    # Fallback: urllib
    try:
        import urllib.request
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=body, method="POST")
        for k, v in headers.items():
            request.add_header(k, v)
        with urllib.request.urlopen(request, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            try:
                response_text = data["content"][0]["text"]
                return _parse_scores(response_text, len(thumbnail_b64s))
            except (KeyError, IndexError, TypeError):
                logger.warning("Unexpected Codex Vision response: %s", data)
                return None
    except Exception as e:
        logger.warning("Codex Vision API call failed (urllib): %s", e)
        return None


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _download_image_b64(url: str) -> Optional[str]:
    """Download an image and return as base64 string.

    Tries requests first, falls back to urllib.

    Args:
        url: Image URL to download.

    Returns:
        Base64-encoded image data, or None on failure.
    """
    if not url:
        logger.debug("Empty URL passed to _download_image_b64")
        return None

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    # Try requests first
    try:
        import requests as req_lib
        resp = req_lib.get(url, timeout=10, headers=headers)
        if resp.status_code == 200 and resp.content:
            logger.debug(
                "Downloaded image (%d bytes) from %s",
                len(resp.content), url[:60],
            )
            return base64.b64encode(resp.content).decode()
        logger.debug(
            "Image download returned HTTP %d for %s (content=%d bytes)",
            resp.status_code, url[:60], len(resp.content) if resp.content else 0,
        )
        return None
    except ImportError:
        pass
    except Exception as e:
        logger.debug("Image download failed (requests) for %s: %s", url[:60], e)
        return None

    # Fallback: urllib
    try:
        import urllib.request
        request = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(request, timeout=10) as resp:
            data = resp.read()
            if data:
                logger.debug(
                    "Downloaded image (%d bytes, urllib) from %s",
                    len(data), url[:60],
                )
                return base64.b64encode(data).decode()
        return None
    except Exception as e:
        logger.debug("Image download failed (urllib) for %s: %s", url[:60], e)
        return None


def _parse_scores(text: str, expected_count: int) -> Optional[List[int]]:
    """Parse a JSON array of integer scores from an LLM response.

    Handles common formatting issues like markdown code blocks,
    trailing commas, or extra whitespace.

    Args:
        text: Raw response text from the vision model.
        expected_count: Expected number of scores.

    Returns:
        List of integer scores, or None if parsing fails.
    """
    # Strip markdown code blocks if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        # Remove opening ```json or ``` and closing ```
        cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        cleaned = cleaned.strip()

    try:
        scores = json.loads(cleaned)
        if isinstance(scores, list) and len(scores) == expected_count:
            # Clamp all values to 0-100
            return [max(0, min(100, int(s))) for s in scores]
        logger.warning(
            "Score array length mismatch: got %d, expected %d",
            len(scores) if isinstance(scores, list) else -1,
            expected_count,
        )
        return None
    except (json.JSONDecodeError, ValueError, TypeError) as e:
        logger.warning("Failed to parse vision scores: %s (text: %s)", e, text[:100])
        return None
