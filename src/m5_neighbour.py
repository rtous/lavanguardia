"""Neighbour (paraphrase) calibration: does the model prefer the ORIGINAL WORDING over rewrites with the same facts?

For each passage we score the original and its rewrites (same facts and names, different wording) with the
target model. score = loss(original) - mean loss(rewrites). Knowing the *facts* (world knowledge, from any source)
lowers the loss of both and cancels; only knowing the *wording* makes the original specifically easier.
Members vs controls are then compared (a member effect = memorised wording, not just knowledge of the events).
Rewrites come from data/decop/paraphrases*.jsonl (full = free rewrite; minimal = a few word swaps).

Backends: MLX (default) or transformers on CUDA with --model hf:<repo> (Colab; precision via --precision or env
HF_PRECISION, see src/hf_load.py). Same scoring function in both (m5_logprob.scores == m5_hf.scores); the HF rows
record precision and weights commit.

Usage: python -I src/m5_neighbour.py --model mlx-community/gemma-2-9b-4bit --out results/m5_neighbour_gemma2_9b.jsonl
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))

SRC = {"full": "data/decop/paraphrases.jsonl", "minimal": "data/decop/paraphrases_minimal.jsonl"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True); ap.add_argument("--out", required=True)
    ap.add_argument("--max-tokens", type=int, default=384)
    ap.add_argument("--src", nargs="+", default=None, help="path:style pairs (default: the DE-COP paraphrase files)")
    ap.add_argument("--precision", default=None, help="hf: models only: auto|bf16|fp16|int8|int4")
    a = ap.parse_args()
    if a.model.startswith("hf:"):
        from hf_load import load
        from m5_hf import scores as hf_scores
        model, tok, info = load(a.model[3:], a.precision)
        scores = lambda m, t, text, n: hf_scores(m, t, text, n, m.device)  # noqa: E731
    else:
        from mlx_lm import load
        from m5_logprob import scores
        (model, tok), info = load(a.model), {}
    done = set()
    if os.path.exists(a.out):
        done = {(r["id"], r["set"], r["style"]) for r in map(json.loads, open(a.out))}
    with open(a.out, "a") as f:
        src = dict(reversed(x.rsplit(":", 1)) for x in a.src) if a.src else SRC
        for style, path in src.items():
            for d in map(json.loads, open(path, encoding="utf-8")):
                if (d["id"], d["set"], style) in done:
                    continue
                o = scores(model, tok, d["passage"], a.max_tokens)
                ps = [scores(model, tok, p, a.max_tokens) for p in d["paraphrases"]]
                if o is None or any(p is None for p in ps):
                    continue
                f.write(json.dumps({"id": d["id"], "set": d["set"], "pub_date": d["pub_date"], "style": style, "group": d.get("group"),
                                    "model": a.model, **info, "orig": o, "paras": ps}) + "\n")
                f.flush()
    print("done", a.out)


if __name__ == "__main__":
    main()
