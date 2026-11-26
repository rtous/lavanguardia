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


_gclient = None


def gemini_client():
    global _gclient
    if _gclient is None:
        from dotenv import dotenv_values
        from google import genai
        from google.genai import types
        key = os.environ.get("GEMINI_API_KEY") or dotenv_values(".env").get("GEMINI_API_KEY")
        _gclient = genai.Client(api_key=key, http_options=types.HttpOptions(api_version="v1beta"))
    return _gclient


GEMINI_TOOLS = {"google_search": lambda t: t.Tool(google_search=t.GoogleSearch()),
                "url_context": lambda t: t.Tool(url_context=t.UrlContext())}


def ask_gemini(experiment, model, user, system=None, max_tokens=1024, meta=None, tools=()):
    """tools: names from GEMINI_TOOLS (retrieval tests, M4). Empty = no browsing (default)."""
    from google.genai import types
    contents = user if isinstance(user, str) else [
        types.Content(role="model" if m["role"] == "assistant" else "user", parts=[types.Part(text=m["content"])]) for m in user]
    params = {"model": model, "contents": user, "tools": list(tools),
              "config": {"temperature": 0, "max_output_tokens": max(max_tokens, 2048),
                         **({"system_instruction": system} if system else {})}}
    t0 = time.time()
    raw, text, rmodel, stop, rid = None, "", None, None, None
    for attempt in range(8):
        try:
            r = gemini_client().models.generate_content(model=model, contents=contents,
                                                        config=types.GenerateContentConfig(
                                                            **params["config"],
                                                            **({"tools": [GEMINI_TOOLS[n](types) for n in tools]} if tools else {})))
            raw = r.model_dump(mode="json", exclude_none=True)
            text = r.text or ""
            rmodel, rid = r.model_version, r.response_id
            stop = str(r.candidates[0].finish_reason) if r.candidates else "no_candidates"
            break
        except Exception as e:
            msg = str(e)
            raw, stop = {"error": msg[:500]}, "api_error"
            if "client has been closed" in msg:
                global _gclient
                _gclient = None
                continue
            if "limit: 0" in msg or "per day" in msg.lower():  # unrecoverable quota: do not retry
                break
            if any(c in msg for c in ("429", "503", "500", "RESOURCE_EXHAUSTED", "UNAVAILABLE")):
                time.sleep(min(120, 10 * (attempt + 1)))
                continue
            break
    rec = {"ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "provider": "google",
           "model_requested": model, "model_reported": rmodel, "request_id": rid, "stop_reason": stop,
           "latency_s": round(time.time() - t0, 2), "meta": meta or {}, "request": params, "response": raw}
    _log(experiment, rec)
    return text, rec


_local = {}


def ask_local(experiment, model, user, system=None, max_tokens=1024, meta=None, raw=False):
    """Open-weight model run locally with MLX (model = Hugging Face id, e.g. mlx-community/...). Greedy decoding, so
    outputs are deterministic. raw=True: `user` is a plain-text prompt continued as-is (base models, no chat template).
    The exact snapshot (commit hash) of the weights is logged for chain of custody. Not thread-safe: use 1 worker."""
    from huggingface_hub import try_to_load_from_cache
    from mlx_lm import load, generate
    from mlx_lm.sample_utils import make_sampler
    if model not in _local:
        _local.clear()
        cfg = try_to_load_from_cache(model, "config.json")
        rev = os.path.basename(os.path.dirname(cfg)) if isinstance(cfg, str) else "unknown"
        _local[model] = (*load(model), rev)
    m, tok, rev = _local[model]
    if raw:
        prompt = user
    else:
        msgs = [{"role": "user", "content": user}] if isinstance(user, str) else list(user)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    t0 = time.time()
    text = generate(m, tok, prompt=prompt, max_tokens=max_tokens, sampler=make_sampler(temp=0.0))
    params = {"model": model, "revision": rev, "raw": raw, "system": system, "user": user, "prompt": prompt,
              "max_tokens": max_tokens, "decoding": "greedy (temp 0)"}
    rec = {"ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "provider": "local-mlx", "model_requested": model,
           "model_reported": f"{model}@{rev}", "request_id": None, "stop_reason": "end", "latency_s": round(time.time() - t0, 2),
           "meta": meta or {}, "request": params, "response": {"text": text}}
    _log(experiment, rec)
    return text, rec


_hf = {}


def ask_hf(experiment, model, user, system=None, max_tokens=1024, meta=None, raw=False):
    """Open-weight model with Hugging Face transformers on a CUDA GPU (e.g. Google Colab). model = "hf:<repo id>".
    Greedy decoding (deterministic). The weights' commit hash is logged, as in ask_local. 1 worker."""
    import sys
    import torch
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))  # python -I drops the script dir
    from hf_load import load
    repo = model[3:]
    if repo not in _hf:
        _hf.clear()
        m, tok, info = load(repo)  # precision from env HF_PRECISION (auto|bf16|fp16|int8|int4)
        _hf[repo] = (m, tok, info["revision"], info["precision"])
    m, tok, rev, prec = _hf[repo]
    if raw or not getattr(tok, "chat_template", None):
        prompt = user if isinstance(user, str) else "\n".join(x["content"] for x in user)
    else:
        msgs = [{"role": "user", "content": user}] if isinstance(user, str) else list(user)
        if system:
            msgs = [{"role": "system", "content": system}] + msgs
        prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
    t0 = time.time()
    enc = tok(prompt, return_tensors="pt", add_special_tokens=raw).to(m.device)
    with torch.no_grad():
        out = m.generate(**enc, max_new_tokens=max_tokens, do_sample=False, pad_token_id=tok.eos_token_id)
    text = tok.decode(out[0, enc["input_ids"].shape[1]:], skip_special_tokens=True)
    params = {"model": repo, "revision": rev, "raw": raw, "system": system, "user": user, "prompt": prompt,
              "max_tokens": max_tokens, "decoding": "greedy", "backend": "transformers", "precision": prec}
    rec = {"ts_utc": dt.datetime.now(dt.timezone.utc).isoformat(), "provider": "hf-transformers", "model_requested": model,
           "model_reported": f"{repo}@{rev}", "request_id": None, "stop_reason": "end", "latency_s": round(time.time() - t0, 2),
           "meta": meta or {}, "request": params, "response": {"text": text}}
    _log(experiment, rec)
    return text, rec


def ask(experiment, model, user, system=None, max_tokens=1024, meta=None, tools=(), raw=False):
    """Text call. `user` is a string (single turn) or a list of {"role": "user"|"assistant", "content"} (multi-turn).
    Returns (text, record). `tools` only for Gemini; `raw` (plain completion) only for local models."""
    if model.startswith(("gemini", "gemma-")):  # Gemma models served by the Gemini API
        return ask_gemini(experiment, model, user, system, max_tokens, meta, tools)
    if model.startswith("hf:"):  # transformers on CUDA (Colab)
        return ask_hf(experiment, model, user, system, max_tokens, meta, raw)
    if "/" in model:
        return ask_local(experiment, model, user, system, max_tokens, meta, raw)
    assert not tools, "tools not implemented for this provider"
    msgs = [{"role": "user", "content": user}] if isinstance(user, str) else list(user)
    params = {"model": model, "max_tokens": max_tokens, "messages": msgs}
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
