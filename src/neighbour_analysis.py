"""Analyse neighbour-calibrated scores (see m5_neighbour.py).

Per passage and feature: gap = orig - mean(rewrites), oriented so that NEGATIVE = original wording is
specifically more familiar than same-facts rewrites. Members vs controls: mean gaps, bootstrap CI of the
difference, one-sided Mann-Whitney, and a dataset-inference-style combined test.

Usage: python -I src/neighbour_analysis.py results/m5_neighbour_*.jsonl --out results/neighbour_summary.json
"""
import argparse, json, os, sys

import numpy as np
from scipy.stats import mannwhitneyu

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import run  # noqa: E402

FEATS = {"loss": 1, "zlib_ratio": 1, "mink": -1, "minkpp": -1}


def gaps(r):
    return [s * (r["orig"][f] - np.mean([p[f] for p in r["paras"]])) for f, s in FEATS.items()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+"); ap.add_argument("--out", required=True)
    a = ap.parse_args()
    rng = np.random.default_rng(0)
    out = {}
    for path in a.files:
        rows = [json.loads(l) for l in open(path)]
        name = os.path.basename(path)[len("m5_neighbour_"):-6]
        for style in ("full", "minimal"):
            R = [r for r in rows if r["style"] == style]
            Gm = np.array([gaps(r) for r in R if r["set"] == "member"]); Gc = np.array([gaps(r) for r in R if r["set"] == "control"])
            if len(Gm) < 20 or len(Gc) < 20:
                continue
            res = {"n_members": len(Gm), "n_controls": len(Gc)}
            for j, f in enumerate(FEATS):
                bs = [rng.choice(Gm[:, j], len(Gm)).mean() - rng.choice(Gc[:, j], len(Gc)).mean() for _ in range(2000)]
                res[f] = {"member_mean": float(Gm[:, j].mean()), "control_mean": float(Gc[:, j].mean()),
                          "diff": float(Gm[:, j].mean() - Gc[:, j].mean()), "ci95": [float(x) for x in np.percentile(bs, [2.5, 97.5])],
                          "p_less": float(mannwhitneyu(Gm[:, j], Gc[:, j], alternative="less").pvalue)}
            res["di_combined"] = run(-Gm, -Gc, 200)["median_p"]
            out[f"{name} | {style}"] = res
            print(f"{name:14s} {style:8s} n={len(Gm)}/{len(Gc)} loss gap mem={res['loss']['member_mean']:+.4f} "
                  f"ctl={res['loss']['control_mean']:+.4f} diff={res['loss']['diff']:+.4f} {np.round(res['loss']['ci95'], 4)} "
                  f"p={res['loss']['p_less']:.3g} | DI p={res['di_combined']:.3g}")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
