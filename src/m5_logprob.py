"""M5: logprob-based membership signals on a local open-weight model (MLX, Apple Silicon).

For each article computes, over the first --max-tokens tokens of the body:
  - loss (mean NLL) / perplexity          lower = more familiar
  - zlib ratio  = NLL_sum / zlib_bits      (Carlini et al. 2021) lower = more familiar
  - Min-K% (k=20)                          (Shi et al. 2024) higher = more familiar
  - Min-K%++ (k=20)                        (Zhang et al. 2024) higher = more familiar
Writes one JSON line per article to --out (scores only, plus id/set/model).

Usage:
  python -I src/m5_logprob.py --model mlx-community/Qwen2.5-7B-4bit \
      --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_qwen25_7b.jsonl
"""
import argparse, json, os, zlib

import mlx.core as mx
import numpy as np
from mlx_lm import load


def scores(model, tok, text, max_tokens, k=0.2):
    ids = tok.encode(text)[: max_tokens + 1]
    if len(ids) < 32:
        return None
    x = mx.array(ids)[None]
    logits = model(x[:, :-1]).astype(mx.float32)[0]          # (T, V)
    logp = logits - mx.logsumexp(logits, axis=-1, keepdims=True)
    tgt = mx.array(ids[1:])
    tok_lp = mx.take_along_axis(logp, tgt[:, None], axis=-1)[:, 0]
    p = mx.exp(logp)
    mu = (p * logp).sum(-1)
    var = (p * logp * logp).sum(-1) - mu * mu
    mkpp = (tok_lp - mu) / mx.sqrt(mx.maximum(var, 1e-6))
    mx.eval(tok_lp, mkpp)
    lp = np.array(tok_lp)
    zz = np.array(mkpp)
    n = max(1, int(len(lp) * k))
    nll_sum = -lp.sum()
    zbits = len(zlib.compress(text.encode("utf-8"))) * 8
    return {
        "n_tokens": int(len(lp)),
        "loss": float(-lp.mean()),
        "zlib_ratio": float(nll_sum / zbits),
        "mink": float(np.sort(lp)[:n].mean()),
        "minkpp": float(np.sort(zz)[:n].mean()),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--inputs", nargs="+", required=True, help="path:label")
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=384)
    a = ap.parse_args()
    model, tok = load(a.model)
    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    done = set()
    if os.path.exists(a.out):
        done = {(json.loads(l)["id"], json.loads(l)["set"]) for l in open(a.out)}
    with open(a.out, "a") as f:
        for spec in a.inputs:
            path, label = spec.rsplit(":", 1)
            for i, line in enumerate(open(path, encoding="utf-8")):
                d = json.loads(line)
                if (d["id"], label) in done:
                    continue
                s = scores(model, tok, d["text"], a.max_tokens)
                if s is None:
                    continue
                f.write(json.dumps({"id": d["id"], "set": label, "pub_date": d["pub_date"], "section": d["section"],
                                    "lang": d["lang"], "model": a.model, **s}) + "\n")
                f.flush()
                if i % 25 == 0:
                    print(label, i, s, flush=True)


if __name__ == "__main__":
    main()
