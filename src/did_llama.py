"""Difference-in-differences membership test with two models of the same family and different training cutoffs.

Llama 3 8B (training data to Mar 2023) vs Llama 3.1 8B (to Dec 2023); same tokenizer, so per-token scores are
directly comparable. For each article: delta = score(Llama 3.1) - score(Llama 3), oriented so that NEGATIVE delta
means "more familiar to Llama 3.1".
Groups:
  BOTH : published Jan 2020 - Feb 2023  (seen by both models)
  NEW  : published Apr - Nov 2023       (seen only by Llama 3.1)   <- the group of interest
  NONE : published Sep 2025 - Mar 2026  (seen by neither)
If training on La Vanguardia leaves a trace, NEW should have a more negative delta than both BOTH and NONE.
Time drift cancels because both models score the very same articles.

Also reports a dataset-inference style test (logistic combination of the 4 deltas, held-out halves, Welch t-test)
for NEW vs NONE and NEW vs BOTH, plus a placebo (BOTH split in two halves by date).

Usage: python -I src/did_llama.py --l3 results/m5_llama3_8b.jsonl --l31 results/m5_llama31_8b.jsonl \
          --l3-new results/m5_mid2023_llama3_8b.jsonl --l31-new results/m5_mid2023_llama31_8b.jsonl --out results/did_llama.json
"""
import argparse, json, os, sys

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import run  # noqa: E402

FEATS = {"loss": 1, "zlib_ratio": 1, "mink": -1, "minkpp": -1}   # orient: lower = more familiar


def load(paths):
    d = {}
    for p in paths:
        for r in map(json.loads, open(p)):
            d[r["id"]] = r
    return d


def deltas(a31, a3, ids):
    return np.array([[s * (a31[i][f] - a3[i][f]) for f, s in FEATS.items()] for i in ids])


def boot_diff(x, y, rng, B=2000):
    bs = [rng.choice(x, len(x)).mean() - rng.choice(y, len(y)).mean() for _ in range(B)]
    return float(np.mean(x) - np.mean(y)), [float(v) for v in np.percentile(bs, [2.5, 97.5])]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l3", required=True); ap.add_argument("--l31", required=True)
    ap.add_argument("--l3-new", required=True); ap.add_argument("--l31-new", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    a3, a31 = load([a.l3, a.l3_new]), load([a.l31, a.l31_new])
    rows3 = {r["id"]: r for p in (a.l3, a.l3_new) for r in map(json.loads, open(p))}
    ids = [i for i in a31 if i in a3]
    grp = {}
    for i in ids:
        d = rows3[i]["pub_date"]
        grp[i] = "BOTH" if d < "20230301" else ("NEW" if "20230401" <= d < "20231201" else ("NONE" if d >= "20250901" else None))
    G = {g: [i for i in ids if grp[i] == g] for g in ("BOTH", "NEW", "NONE")}
    print({g: len(v) for g, v in G.items()})
    rng = np.random.default_rng(0)
    out = {"n": {g: len(v) for g, v in G.items()}, "per_feature": {}}
    for j, f in enumerate(FEATS):
        D = {g: deltas(a31, a3, G[g])[:, j] for g in G}
        res = {g: float(D[g].mean()) for g in G}
        for x, y in (("NEW", "NONE"), ("NEW", "BOTH"), ("BOTH", "NONE")):
            diff, ci = boot_diff(D[x], D[y], rng)
            p = mannwhitneyu(D[x], D[y], alternative="less").pvalue
            res[f"{x}-{y}"] = {"diff": diff, "ci95": ci, "p_less": float(p)}
        out["per_feature"][f] = res
        print(f"{f:10s} mean delta BOTH={res['BOTH']:+.4f} NEW={res['NEW']:+.4f} NONE={res['NONE']:+.4f} | "
              f"NEW-NONE {res['NEW-NONE']['diff']:+.4f} {np.round(res['NEW-NONE']['ci95'],4)} p={res['NEW-NONE']['p_less']:.3g} | "
              f"NEW-BOTH {res['NEW-BOTH']['diff']:+.4f} p={res['NEW-BOTH']['p_less']:.3g}")
    # dataset-inference style (suspect = NEW; more familiar to 3.1 = more negative delta -> flip sign so higher = suspect)
    X = {g: -deltas(a31, a3, G[g]) for g in G}
    out["di_NEW_vs_NONE"] = run(X["NEW"], X["NONE"], 200)
    out["di_NEW_vs_BOTH"] = run(X["NEW"], X["BOTH"], 200)
    b = sorted(G["BOTH"], key=lambda i: rows3[i]["pub_date"]); h = len(b) // 2
    out["placebo_BOTH_old_vs_recent"] = run(-deltas(a31, a3, b[h:]), -deltas(a31, a3, b[:h]), 200)
    for k in ("di_NEW_vs_NONE", "di_NEW_vs_BOTH", "placebo_BOTH_old_vs_recent"):
        print(k, out[k])
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
