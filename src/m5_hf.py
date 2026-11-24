"""M5 with a Hugging Face (PyTorch) causal LM — used for the *temporal-drift baseline*.

A model whose training data predates BOTH member and control publication dates cannot have a membership
signal; any member/control gap it shows is distribution shift (topics, vocabulary over time). Subtract it
from the target model's gap. Default: flax-community/gpt-2-spanish (OSCAR 2019 = Common Crawl Nov 2018).

Same metrics/output format as m5_logprob.py.
Usage: python -I src/m5_hf.py --model flax-community/gpt-2-spanish --inputs data/cc/members.jsonl:member \
          data/cc/controls.jsonl:control --out results/m5_gpt2es.jsonl
"""
import argparse, json, os, zlib

import numpy as np
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


@torch.no_grad()
def scores(model, tok, text, max_tokens, dev, k=0.2):
    ids = tok.encode(text)[: max_tokens + 1]
    if len(ids) < 32:
        return None
    x = torch.tensor([ids], device=dev)
    logits = model(x[:, :-1]).logits[0].float()
    logp = torch.log_softmax(logits, -1)
    tgt = x[0, 1:]
    tok_lp = logp.gather(1, tgt[:, None])[:, 0]
    p = logp.exp()
    mu = (p * logp).sum(-1)
    var = (p * logp * logp).sum(-1) - mu * mu
    zz = ((tok_lp - mu) / var.clamp_min(1e-6).sqrt()).cpu().numpy()
    lp = tok_lp.cpu().numpy()
    n = max(1, int(len(lp) * k))
    return {"n_tokens": int(len(lp)), "loss": float(-lp.mean()),
            "zlib_ratio": float(-lp.sum() / (len(zlib.compress(text.encode("utf-8"))) * 8)),
            "mink": float(np.sort(lp)[:n].mean()), "minkpp": float(np.sort(zz)[:n].mean())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="flax-community/gpt-2-spanish")
    ap.add_argument("--inputs", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=384)
    a = ap.parse_args()
    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(a.model)
    model = AutoModelForCausalLM.from_pretrained(a.model).to(dev).eval()
    done = set()
    if os.path.exists(a.out):
        done = {(json.loads(l)["id"], json.loads(l)["set"]) for l in open(a.out)}
    with open(a.out, "a") as f:
        for spec in a.inputs:
            path, label = spec.rsplit(":", 1)
            for line in open(path, encoding="utf-8"):
                d = json.loads(line)
                if (d["id"], label) in done:
                    continue
                s = scores(model, tok, d["text"], a.max_tokens, dev)
                if s:
                    f.write(json.dumps({"id": d["id"], "set": label, "pub_date": d["pub_date"], "section": d["section"],
                                        "lang": d["lang"], "model": a.model, **s}) + "\n")


if __name__ == "__main__":
    main()
