"""Provider client + append-only evidence log.

Every call is appended to evidence/<experiment>/calls.jsonl with: UTC timestamp, provider, requested model,
model reported by the API, request id, full request params, full raw response, and SHA-256 of
(request JSON + response JSON) so that any later edit of the log is detectable.

Anthropic credentials are resolved by the SDK (ANTHROPIC_API_KEY or the `ant auth login` profile).
Note: since API version 2026-10-21 sampling params (temperature/top_p/top_k) are rejected, so outputs are
not guaranteed deterministic. We record that and, where it matters, repeat calls.
"""
import datetime as dt, hashlib, json, os, threading, time

import anthropic

_lock = threading.Lock()
_client = None


def client():
    global _client
    if _client is None:
        _client = anthropic.Anthropic(max_retries=6)
    return _client


def _log(experiment, record):
    os.makedirs(f"evidence/{experiment}", exist_ok=True)
    body = json.dumps({"request": record["request"], "response": record["response"]}, ensure_ascii=False, sort_keys=True)
    record["sha256"] = hashlib.sha256(body.encode("utf-8")).hexdigest()
    with _lock, open(f"evidence/{experiment}/calls.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


# Models whose thinking is always on (no "disabled"): keep effort low and give room for thinking tokens.
ALWAYS_THINK = ("claude-opus-5-5", "claude-fable", "claude-opus-5", "claude-sonnet-5", "claude-haiku-5-5")


def ask(experiment, model, user, system=None, max_tokens=1024, meta=None):
    """Single-turn text call. Returns (text, record)."""
    params = {"model": model, "max_tokens": max_tokens, "messages": [{"role": "user", "content": user}]}
    if system:
        params["system"] = system
    if model.startswith(ALWAYS_THINK):
        params["output_config"] = {"effort": "low"}
        params["max_tokens"] = max(max_tokens, 4000)
    t0 = time.time()
    try:
        resp = client().messages.create(**params)
        raw = resp.to_dict()
        text = "".join(b.text for b in resp.content if b.type == "text")
        rid, rmodel, stop = resp._request_id, resp.model, resp.stop_reason
    except anthropic.APIStatusError as e:
        raw = {"error": str(e), "status": e.status_code}
        text, rid, rmodel, stop = "", None, None, "api_error"
    rec = {
        "ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "provider": "anthropic",
        "model_requested": model, "model_reported": rmodel, "request_id": rid, "stop_reason": stop,
        "latency_s": round(time.time() - t0, 2), "meta": meta or {},
        "request": params, "response": raw,
    }
    _log(experiment, rec)
    return text, rec
