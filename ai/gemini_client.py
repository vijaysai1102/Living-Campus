import json
import re
from groq import Groq
from config.settings import GROQ_API_KEY, GROQ_MODEL

_client = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        if not GROQ_API_KEY:
            raise ValueError("GROQ_API_KEY is not set. Add it to your .env file.")
        _client = Groq(api_key=GROQ_API_KEY)
    return _client


def generate_response(prompt: str) -> dict:
    client = _get_client()
    try:
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.85,
            max_tokens=1024
        )
        raw = response.choices[0].message.content.strip()
        return _parse_response(raw)
    except Exception as e:
        err = str(e)
        if "429" in err or "rate" in err.lower():
            raise QuotaExceededError("Groq rate limit hit. Wait a moment and try again.")
        if "404" in err or "model_not_found" in err or "does not exist" in err:
            raise ModelNotFoundError(
                f"Groq model '{GROQ_MODEL}' was not found or has been deprecated. "
                "Please update GROQ_MODEL in your .env or Streamlit secrets (recommended: 'qwen/qwen3.8-27b')."
            )
        raise


def _safe_int(value, default: int) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _normalize_delta(raw_delta) -> dict:
    if not isinstance(raw_delta, dict):
        return {}
    normalized = {}
    for key, value in raw_delta.items():
        try:
            normalized[str(key).lower()] = int(value)
        except (TypeError, ValueError):
            continue
    return normalized


def _normalize_shareable_facts(raw) -> list[str]:
    if not raw:
        return []
    if isinstance(raw, str):
        raw = [raw]
    if not isinstance(raw, list):
        return []
    facts = []
    for item in raw:
        if isinstance(item, str):
            text = item.strip()
        elif isinstance(item, dict):
            text = str(item.get("text") or item.get("fact") or "").strip()
        else:
            continue
        if text:
            facts.append(text)
        if len(facts) >= 2:
            break
    return facts


def _normalize_promise_status(value) -> str:
    status = str(value or "").strip().lower()
    return status if status in {"kept", "broken"} else ""


def _parse_bool(value, default: bool = False) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"true", "yes", "1"}
    if isinstance(value, (int, float)):
        return bool(value)
    return default


def _parse_response(raw: str) -> dict:
    cleaned = re.sub(r"```json\s*", "", raw)
    cleaned = re.sub(r"```\s*", "", cleaned).strip()
    # Fix invalid JSON: strip // comments
    cleaned = re.sub(r"//[^\n\"]*", "", cleaned)
    # Fix invalid JSON: +5 → 5 (JSON doesn't allow leading +)
    cleaned = re.sub(r":\s*\+(\d)", r": \1", cleaned)
    empty = {
        "reply": raw,
        "emotion_delta": {},
        "relationship_delta": {},
        "memory_note": "",
        "memory_kind": "fact",
        "memory_importance": 5,
        "memory_tags": "",
        "shareable_facts": [],
        "keep_secret": False,
        "fact_sensitivity": 40,
        "observed_trait": "",
        "promise_status": "",
    }
    try:
        data = json.loads(cleaned)
        sensitivity = data.get("fact_sensitivity", 40)
        try:
            sensitivity = max(0, min(100, int(sensitivity)))
        except (TypeError, ValueError):
            sensitivity = 40
        return {
            "reply": data.get("reply", raw),
            "emotion_delta": _normalize_delta(data.get("emotion_delta", {})),
            "relationship_delta": _normalize_delta(data.get("relationship_delta", {})),
            "memory_note": data.get("memory_note", "") or "",
            "memory_kind": str(data.get("memory_kind") or "fact").lower().strip(),
            "memory_importance": _safe_int(data.get("memory_importance", 5), 5),
            "memory_tags": data.get("memory_tags", "") or "",
            "shareable_facts": _normalize_shareable_facts(data.get("shareable_facts", [])),
            "keep_secret": _parse_bool(data.get("keep_secret", False)),
            "fact_sensitivity": sensitivity,
            "observed_trait": str(data.get("observed_trait") or "").strip(),
            "promise_status": _normalize_promise_status(data.get("promise_status", "")),
        }
    except (json.JSONDecodeError, ValueError):
        return empty


def ping() -> str:
    client = _get_client()
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": "Say 'API connection successful' and nothing else."}],
        max_tokens=20
    )
    return response.choices[0].message.content.strip()


class QuotaExceededError(Exception):
    pass


class ModelNotFoundError(Exception):
    pass
