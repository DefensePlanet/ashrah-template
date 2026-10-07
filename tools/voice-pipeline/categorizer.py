"""Content classification for voice recordings.

Three-tier approach:
1. Duration pre-filter: <3s -> ambient (skip transcription)
2. Keyword fast-path: 3+ prayer keywords -> prayer (high confidence)
3. Ollama LLM fallback: JSON prompt for category + confidence + summary

Follows the Ollama urllib.request pattern from Catalyst's file-organizer/categorizer.py.
"""

import json
import logging
from typing import Dict, List, Optional, Tuple
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

# Ollama API endpoint
OLLAMA_URL = "http://localhost:11434"


# ---------------------------------------------------------------------------
# Ollama API client (urllib.request pattern from file-organizer)
# ---------------------------------------------------------------------------

def _ollama_available() -> bool:
    """Check if Ollama is running."""
    try:
        req = Request(f"{OLLAMA_URL}/api/tags")
        with urlopen(req, timeout=5) as resp:
            return resp.status == 200
    except Exception:
        return False


def _model_available(model: str) -> bool:
    """Check if a specific model is available in Ollama."""
    try:
        req = Request(f"{OLLAMA_URL}/api/tags")
        with urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
            names = [m["name"] for m in data.get("models", [])]
            return model in names or any(n.startswith(model) for n in names)
    except Exception:
        return False


def _ollama_generate(
    model: str,
    prompt: str,
    timeout: int = 60,
) -> Optional[str]:
    """Call Ollama generate API.

    Args:
        model: Ollama model name.
        prompt: The prompt text.
        timeout: Request timeout in seconds.

    Returns:
        Response text from the model, or None on failure.
    """
    payload = {
        "model": model,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 300,
        },
    }

    data = json.dumps(payload).encode("utf-8")
    req = Request(
        f"{OLLAMA_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )

    try:
        with urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read())
            return result.get("response", "")
    except Exception as e:
        logger.error("Ollama generate failed: %s", e)
        return None


# ---------------------------------------------------------------------------
# Keyword matching
# ---------------------------------------------------------------------------

def _count_keyword_matches(text: str, keywords: List[str]) -> int:
    """Count how many keywords appear in the text (case-insensitive)."""
    text_lower = text.lower()
    return sum(1 for kw in keywords if kw.lower() in text_lower)


def _keyword_classify(
    transcript: str,
    categories: dict,
) -> Optional[Tuple[str, float, str]]:
    """Attempt fast keyword-based classification.

    Args:
        transcript: Full transcript text.
        categories: Category config dict from config.yaml.

    Returns:
        Tuple of (category, confidence, summary) if confident match found,
        or None if keyword match is insufficient.
    """
    if not transcript.strip():
        return None

    best_cat = None
    best_count = 0

    for cat_name, cat_config in categories.items():
        keywords = cat_config.get("keywords", [])
        if not keywords:
            continue
        count = _count_keyword_matches(transcript, keywords)
        if count > best_count:
            best_count = count
            best_cat = cat_name

    # Require at least 3 keyword matches for confident classification
    if best_cat and best_count >= 3:
        # Build a simple summary from first sentence
        first_sentence = transcript.strip().split(".")[0][:100]
        summary = first_sentence.strip()
        if not summary.endswith("."):
            summary += "..."

        confidence = min(0.90, 0.70 + (best_count * 0.05))
        logger.info(
            "Keyword fast-path: %s (count=%d, confidence=%.2f)",
            best_cat, best_count, confidence,
        )
        return (best_cat, confidence, summary)

    return None


# ---------------------------------------------------------------------------
# LLM classification
# ---------------------------------------------------------------------------

def _build_llm_prompt(
    transcript: str,
    duration_secs: float,
    categories: dict,
) -> str:
    """Build the classification prompt for the LLM."""
    cat_descriptions = []
    for cat_name, cat_config in categories.items():
        desc = cat_config.get("description", "")
        cat_descriptions.append(f"- {cat_name}: {desc}")

    categories_block = "\n".join(cat_descriptions)

    # Truncate transcript to first 2000 chars
    transcript_preview = transcript[:2000] if len(transcript) > 2000 else transcript

    return f"""Classify this voice recording transcript into exactly ONE category.

Categories:
{categories_block}

Duration: {duration_secs:.1f} seconds
Transcript (first 2000 chars):
---
{transcript_preview}
---

Respond with ONLY valid JSON:
{{"category": "...", "confidence": 0.85, "summary": "one-line summary"}}"""


def _parse_llm_response(
    response: str,
    valid_categories: List[str],
) -> Optional[Tuple[str, float, str]]:
    """Parse LLM JSON response and validate category.

    Args:
        response: Raw text response from LLM.
        valid_categories: List of allowed category names.

    Returns:
        Tuple of (category, confidence, summary) or None on parse failure.
    """
    text = response.strip()

    # Strip markdown code fences
    if text.startswith("```"):
        lines = text.split("\n")
        lines = [line for line in lines if not line.strip().startswith("```")]
        text = "\n".join(lines)

    # Find JSON object
    start = text.find("{")
    end = text.rfind("}") + 1
    if start == -1 or end == 0:
        logger.warning("No JSON found in LLM response")
        return None

    try:
        data = json.loads(text[start:end])
    except json.JSONDecodeError as e:
        logger.warning("JSON parse error in LLM response: %s", e)
        return None

    category = data.get("category", "")
    confidence = float(data.get("confidence", 0.5))
    summary = str(data.get("summary", ""))[:200]

    # Validate category is in allowed list
    if category not in valid_categories:
        # Try case-insensitive match
        cat_lower = {c.lower(): c for c in valid_categories}
        category = cat_lower.get(category.lower(), "uncategorized")

    # Clamp confidence
    confidence = max(0.0, min(1.0, confidence))

    return (category, confidence, summary)


def _llm_classify(
    transcript: str,
    duration_secs: float,
    config: dict,
) -> Optional[Tuple[str, float, str]]:
    """Classify using Ollama LLM.

    Args:
        transcript: Full transcript text.
        duration_secs: Recording duration in seconds.
        config: Categorizer config dict.

    Returns:
        Tuple of (category, confidence, summary) or None on failure.
    """
    model = config.get("model", "llama3.2:3b")
    categories = config.get("categories", {})
    valid_categories = list(categories.keys())

    if not _ollama_available():
        logger.warning("Ollama not available -- cannot use LLM classification")
        return None

    if not _model_available(model):
        logger.warning("Model %s not available in Ollama", model)
        return None

    prompt = _build_llm_prompt(transcript, duration_secs, categories)
    response = _ollama_generate(model, prompt)

    if not response:
        return None

    return _parse_llm_response(response, valid_categories)


# ---------------------------------------------------------------------------
# Main categorize function
# ---------------------------------------------------------------------------

def categorize(
    transcript: str,
    duration_secs: float,
    config: dict,
) -> Dict[str, object]:
    """Classify a voice recording into a category.

    Three-tier approach:
    1. Duration pre-filter: ambient if very short
    2. Keyword fast-path: high-confidence match on keyword count
    3. Ollama LLM fallback: full text classification

    Args:
        transcript: Transcript text (empty string for ambient recordings).
        duration_secs: Duration of the recording in seconds.
        config: Categorizer config dict from config.yaml.

    Returns:
        Dict with 'category', 'confidence', and 'summary' keys.
    """
    categories = config.get("categories", {})
    ambient_max = config.get("ambient_max_duration", 3.0)
    confidence_threshold = config.get("confidence_threshold", 0.7)

    # Tier 1: Duration pre-filter
    if duration_secs < ambient_max:
        logger.info("Duration %.1fs < %.1fs -- classified as ambient", duration_secs, ambient_max)
        return {
            "category": "ambient",
            "confidence": 0.95,
            "summary": f"Short recording ({duration_secs:.1f}s) -- likely accidental",
        }

    # Tier 1b: Empty transcript after transcription -> ambient
    if not transcript.strip():
        logger.info("Empty transcript -- classified as ambient")
        return {
            "category": "ambient",
            "confidence": 0.90,
            "summary": "No intelligible speech detected",
        }

    # Tier 2: Keyword fast-path
    keyword_result = _keyword_classify(transcript, categories)
    if keyword_result:
        cat, conf, summary = keyword_result
        return {
            "category": cat,
            "confidence": conf,
            "summary": summary,
        }

    # Tier 3: Ollama LLM classification
    llm_result = _llm_classify(transcript, duration_secs, config)
    if llm_result:
        cat, conf, summary = llm_result
        # Apply confidence threshold
        if conf < confidence_threshold:
            logger.info(
                "LLM confidence %.2f below threshold %.2f -- marking uncategorized",
                conf, confidence_threshold,
            )
            return {
                "category": "uncategorized",
                "confidence": conf,
                "summary": summary,
            }
        return {
            "category": cat,
            "confidence": conf,
            "summary": summary,
        }

    # Fallback: keyword-only (lower threshold) if LLM unavailable
    if transcript.strip():
        # Try with lower threshold (any keyword match)
        for cat_name, cat_config in categories.items():
            keywords = cat_config.get("keywords", [])
            count = _count_keyword_matches(transcript, keywords)
            if count >= 1:
                first_sentence = transcript.strip().split(".")[0][:100]
                return {
                    "category": cat_name,
                    "confidence": 0.50,
                    "summary": first_sentence.strip(),
                }

    # Ultimate fallback
    logger.info("All classification methods failed -- uncategorized")
    return {
        "category": "uncategorized",
        "confidence": 0.30,
        "summary": "Classification unavailable",
    }
