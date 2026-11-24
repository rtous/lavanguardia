"""Reference-calibrated membership test (Carlini et al. 2021 "reference model" idea).

For each article: delta = score(target) - score(reference), where the reference model's training data
predates both members and controls (so it carries topic/time drift but no membership). Membership shows up
as members having a more "familiar" delta than controls.

Usage: python -I src/calibrate.py results/m5_qwen25_7b.jsonl results/m5_gpt2es.jsonl
"""
import json, sys

import numpy as np
from scipy.stats import mannwhitneyu

SIGN = {"loss": -1, "zlib_ratio": -1, "mink": 1, "minkpp": 1}


def load(p):
    return {(r["id"], r["set"]): r for r in map(json.loads, open(p))}


def main():
    tgt, ref = load(sys.argv[1]), load(sys.argv[2])
    keys = sorted(set(tgt) & set(ref))
    m = [k for k in keys if k[1] == "member"]; c = [k for k in keys if k[1] == "control"]
    print(f"target={sys.argv[1]} reference={sys.argv[2]} members={len(m)} controls={len(c)}")
    rng = np.random.default_rng(0)
    for met, s in SIGN.items():
        for name, f in (("raw target", lambda k: tgt[k][met]), ("raw reference", lambda k: ref[k][met]),
                        ("calibrated", lambda k: tgt[k][met] - ref[k][met])):
            pos = s * np.array([f(k) for k in m]); neg = s * np.array([f(k) for k in c])
            u = mannwhitneyu(pos, neg, alternative="greater")
            auc = u.statistic / (len(pos) * len(neg))
            boots = []
            for _ in range(300):
                bp, bn = rng.choice(pos, len(pos)), rng.choice(neg, len(neg))
                boots.append(mannwhitneyu(bp, bn).statistic / (len(bp) * len(bn)))
            lo, hi = np.percentile(boots, [2.5, 97.5])
            print(f"  {met:10s} {name:14s} AUC={auc:.3f} [{lo:.3f},{hi:.3f}] p={u.pvalue:.1e}")


if __name__ == "__main__":
    main()
