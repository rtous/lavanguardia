"""Sign-constrained dataset inference: a pre-registered combination that cannot exploit miscalibration.

The learned (logistic) combination of Maini et al. may give a feature a NEGATIVE weight, i.e. treat "less familiar
than expected" as evidence, which turns reference-model miscalibration into significance. Here the direction is fixed
in advance: each calibrated feature is oriented so that higher = more familiar to the target, standardised on the
controls, and the four are averaged with equal weights. One-sided Welch t-test (members > controls), matched groups.

Usage: python -I src/di_fixed.py  -> results/di_fixed.json
"""
import json, os, sys

import numpy as np
from scipy.stats import ttest_ind

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import load  # noqa: E402
from di_matched import meta, match  # noqa: E402
from di_summary import TARGETS, REFS  # noqa: E402

SIGN = {"loss": -1, "zlib_ratio": -1, "mink": 1, "minkpp": 1}


def score(T, R, keys, mode):
    X = []
    for k in keys:
        X.append([SIGN[f] * (T[k][f] - (R[k][f] if mode == "calibrated" else 0) if mode != "reference" else SIGN[f] * R[k][f])
                  for f in SIGN])
    return np.array(X)


def main():
    M = meta([("data/cc/members.jsonl", "member"), ("data/cc/controls.jsonl", "control")])
    out = {}
    for tname, t in TARGETS.items():
        for rname, (r, md) in REFS.items():
            T, R = load(f"results/m5_{t}.jsonl"), load(f"results/m5_{r}.jsonl")
            if md:
                T = {k: v for k, v in T.items() if not (k[1] == "member" and v["pub_date"] < md)}
            keys = [k for k in sorted(set(T) & set(R) & set(M)) if not M[k]["live"]]
            mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
            P = match(mk, ck, M); pm = [p[0] for p in P]; pc = [p[1] for p in P]
            res = {}
            for mode in ("target", "reference", "calibrated"):
                Xm, Xc = score(T, R, pm, mode), score(T, R, pc, mode)
                mu, sd = Xc.mean(0), Xc.std(0) + 1e-9
                sm, sc = ((Xm - mu) / sd).mean(1), ((Xc - mu) / sd).mean(1)
                res[mode] = {"effect_sd": float(sm.mean() - sc.mean()),
                             "p": float(ttest_ind(sm, sc, equal_var=False, alternative="greater").pvalue)}
            out[f"{tname} | {rname}"] = res
            print(f"{tname:16s} {rname:20s} " + "  ".join(f"{m}: d={v['effect_sd']:+.3f} p={v['p']:.2g}" for m, v in res.items()))
    json.dump(out, open("results/di_fixed.json", "w"), indent=1)


if __name__ == "__main__":
    main()
