"""Compare member vs control score distributions: AUC (with bootstrap 95% CI) and Mann-Whitney p-value.

Usage: python -I src/evaluate.py results/m5_qwen25_7b.jsonl [--by lang]
Direction: for loss and zlib_ratio lower = more familiar; for mink/minkpp higher = more familiar.
AUC is reported as P(member looks more familiar than control); 0.5 = no signal.
"""
import argparse, json
from collections import defaultdict

import numpy as np
from scipy.stats import mannwhitneyu

METRICS = {"loss": -1, "zlib_ratio": -1, "mink": 1, "minkpp": 1}


def auc(pos, neg):
    u = mannwhitneyu(pos, neg, alternative="greater")
    return u.statistic / (len(pos) * len(neg)), u.pvalue


def report(rows, title):
    m = [r for r in rows if r["set"] == "member"]
    c = [r for r in rows if r["set"] == "control"]
    print(f"\n== {title}: members={len(m)} controls={len(c)}")
    if len(m) < 5 or len(c) < 5:
        print("  (too few)"); return
    rng = np.random.default_rng(0)
    for k, sign in METRICS.items():
        pos = sign * np.array([r[k] for r in m]); neg = sign * np.array([r[k] for r in c])
        a, p = auc(pos, neg)
        boots = [auc(rng.choice(pos, len(pos)), rng.choice(neg, len(neg)))[0] for _ in range(500)]
        lo, hi = np.percentile(boots, [2.5, 97.5])
        print(f"  {k:11s} AUC={a:.3f}  95%CI=[{lo:.3f},{hi:.3f}]  p={p:.2e}  "
              f"mean member={np.mean([r[k] for r in m]):.3f} control={np.mean([r[k] for r in c]):.3f}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--by", default=None)
    a = ap.parse_args()
    rows = [json.loads(l) for l in open(a.path)]
    report(rows, "ALL")
    if a.by:
        g = defaultdict(list)
        for r in rows:
            g[r[a.by]].append(r)
        for key, rs in sorted(g.items()):
            report(rs, f"{a.by}={key}")


if __name__ == "__main__":
    main()
