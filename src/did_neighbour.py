"""Neighbour test inside the Llama-3 vs Llama-3.1 difference-in-differences: wording vs events.

Per passage and model: gap = loss(original) - mean loss(3 same-facts rewrites)  (negative = original wording preferred).
Per passage: dgap = gap(Llama-3.1) - gap(Llama-3)  (negative = 3.1 gained a preference for the ORIGINAL WORDING).
Knowing the events of mid-2023 lowers the loss of original and rewrites alike, so it cancels in gap; drift cancels
because the same passages are scored by both models. Prediction if 3.1 trained on the text: dgap(NEW) < dgap(BOTH), dgap(NONE).
Pre-registered: one-sided Welch t-test and Mann-Whitney on loss; equal-weight oriented z-score combination of 4 scores.

Usage: python -I src/did_neighbour.py --l3 results/m5_neighbour_mid2023_llama3_8b.jsonl \
          --l31 results/m5_neighbour_mid2023_llama31_8b.jsonl --out results/did_neighbour.json
"""
import argparse, json

import numpy as np
from scipy.stats import mannwhitneyu, ttest_ind

FEATS = {"loss": 1, "zlib_ratio": 1, "mink": -1, "minkpp": -1}   # oriented: lower = more familiar


def gaps(r):
    return np.array([s * (r["orig"][f] - np.mean([p[f] for p in r["paras"]])) for f, s in FEATS.items()])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--l3", required=True); ap.add_argument("--l31", required=True); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    ld = lambda p: {(r["id"], r["group"]): r for r in map(json.loads, open(p))}
    A3, A31 = ld(a.l3), ld(a.l31)
    keys = sorted(set(A3) & set(A31))
    D = {g: np.array([gaps(A31[k]) - gaps(A3[k]) for k in keys if k[1] == g]) for g in ("BOTH", "NEW", "NONE")}
    G3 = {g: np.array([gaps(A3[k]) for k in keys if k[1] == g]) for g in D}
    out = {"n": {g: len(v) for g, v in D.items()}, "mean_dgap": {g: dict(zip(FEATS, v.mean(0).round(5).tolist())) for g, v in D.items()},
           "mean_gap_llama3": {g: dict(zip(FEATS, v.mean(0).round(5).tolist())) for g, v in G3.items()}, "tests": {}}
    print("n", out["n"]); print("mean dgap (3.1 - 3)", out["mean_dgap"])
    rng = np.random.default_rng(0)
    for x, y in (("NEW", "NONE"), ("NEW", "BOTH"), ("BOTH", "NONE")):
        lx, ly = D[x][:, 0], D[y][:, 0]
        bs = [rng.choice(lx, len(lx)).mean() - rng.choice(ly, len(ly)).mean() for _ in range(2000)]
        mu, sd = D[y].mean(0), D[y].std(0) + 1e-12
        zx, zy = (-(D[x] - mu) / sd).mean(1), (-(D[y] - mu) / sd).mean(1)   # higher = more original-wording gain
        t = {"loss_diff": float(lx.mean() - ly.mean()), "loss_ci95": [float(v) for v in np.percentile(bs, [2.5, 97.5])],
             "loss_p_mw_less": float(mannwhitneyu(lx, ly, alternative="less").pvalue),
             "loss_p_welch_less": float(ttest_ind(lx, ly, equal_var=False, alternative="less").pvalue),
             "combined_effect_sd": float(zx.mean() - zy.mean()),
             "combined_p": float(ttest_ind(zx, zy, equal_var=False, alternative="greater").pvalue)}
        out["tests"][f"{x}_vs_{y}"] = t
        print(f"{x} vs {y}: loss dgap diff={t['loss_diff']:+.4f} {np.round(t['loss_ci95'], 4)} p_mw={t['loss_p_mw_less']:.3g} "
              f"| combined d={t['combined_effect_sd']:+.3f} p={t['combined_p']:.3g}")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
