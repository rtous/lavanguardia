"""Dataset inference (Maini et al., NeurIPS 2024), adapted with drift calibration.

Question: was the *suspect set* (members) as a whole used to train the target model, compared with a
*validation set* (controls) that it certainly did not see?

Procedure (repeated over R random splits):
  1. Per article, features = several membership scores (loss, zlib ratio, Min-K%, Min-K%++), each calibrated
     as target - reference (reference model predates both sets -> removes time drift).
  2. Split members and controls into halves A and B.
  3. On A, fit a logistic regression that learns how to *combine* the features (member=1, control=0).
  4. On B (unseen by step 3), score every article and run a one-sided Welch t-test:
     are members' combined scores higher than controls'?
  5. Report the median p-value over splits (and the fraction of splits with p<0.05).
Sanity checks:
  - "null": split the *controls* into two fake groups -> must NOT be significant (false-positive check).
  - "reference only": use the reference model's raw scores -> measures what drift alone produces.
  - sample-size curve: subsample N members/controls to see how significance grows with N.

Usage: python -I src/dataset_inference.py results/m5_qwen25_7b.jsonl results/m5_gpt2es.jsonl --out results/di_qwen25.json
"""
import argparse, json

import numpy as np
from scipy.stats import ttest_ind
from sklearn.linear_model import LogisticRegression
from sklearn.preprocessing import StandardScaler

FEATS = ["loss", "zlib_ratio", "mink", "minkpp"]


def load(p):
    return {(r["id"], r["set"]): r for r in map(json.loads, open(p))}


def features(tgt, ref, keys, mode):
    if mode == "calibrated":
        return np.array([[tgt[k][f] - ref[k][f] for f in FEATS] for k in keys])
    if mode == "target":
        return np.array([[tgt[k][f] for f in FEATS] for k in keys])
    return np.array([[ref[k][f] for f in FEATS] for k in keys])


def di_once(Xm, Xc, rng):
    im, ic = rng.permutation(len(Xm)), rng.permutation(len(Xc))
    am, bm = im[: len(im) // 2], im[len(im) // 2:]
    ac, bc = ic[: len(ic) // 2], ic[len(ic) // 2:]
    XA = np.vstack([Xm[am], Xc[ac]]); yA = np.r_[np.ones(len(am)), np.zeros(len(ac))]
    sc = StandardScaler().fit(XA)
    clf = LogisticRegression(C=1.0, max_iter=1000).fit(sc.transform(XA), yA)
    sm = clf.decision_function(sc.transform(Xm[bm])); scn = clf.decision_function(sc.transform(Xc[bc]))
    return ttest_ind(sm, scn, equal_var=False, alternative="greater").pvalue


def run(Xm, Xc, R, seed=0):
    rng = np.random.default_rng(seed)
    ps = np.array([di_once(Xm, Xc, rng) for _ in range(R)])
    return {"median_p": float(np.median(ps)), "frac_p_lt_0.05": float(np.mean(ps < 0.05)),
            "n_members": int(len(Xm)), "n_controls": int(len(Xc))}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("reference")
    ap.add_argument("--R", type=int, default=200)
    ap.add_argument("--min-member-date", default="", help="drop members published before YYYYMMDD (e.g. reference-model cutoff)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tgt, ref = load(a.target), load(a.reference)
    if a.min_member_date:
        tgt = {k: v for k, v in tgt.items() if not (k[1] == "member" and v["pub_date"] < a.min_member_date)}
    keys = sorted(set(tgt) & set(ref))
    mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
    out = {}
    for mode in ("calibrated", "target", "reference"):
        out[mode] = run(features(tgt, ref, mk, mode), features(tgt, ref, ck, mode), a.R)
        print(f"{mode:11s} {out[mode]}")
    # null check: controls vs controls
    Xc = features(tgt, ref, ck, "calibrated"); rng = np.random.default_rng(1)
    nulls = []
    for _ in range(50):
        perm = rng.permutation(len(Xc)); h = len(perm) // 2
        nulls.append(run(Xc[perm[:h]], Xc[perm[h:]], 20, seed=int(rng.integers(1e9)))["median_p"])
    out["null_controls_vs_controls"] = {"median_of_median_p": float(np.median(nulls)),
                                        "frac_median_p_lt_0.05": float(np.mean(np.array(nulls) < 0.05))}
    print("null       ", out["null_controls_vs_controls"])
    # sample-size curve (calibrated)
    Xm_all, Xc_all = features(tgt, ref, mk, "calibrated"), features(tgt, ref, ck, "calibrated")
    curve = []
    rng = np.random.default_rng(2)
    for n in (50, 100, 200, 300, 448):
        n_m, n_c = min(n, len(Xm_all)), min(n, len(Xc_all))
        reps = []
        for _ in range(20):
            reps.append(run(Xm_all[rng.choice(len(Xm_all), n_m, replace=False)],
                            Xc_all[rng.choice(len(Xc_all), n_c, replace=False)], 30, seed=int(rng.integers(1e9))))
        curve.append({"n_per_group": n, "median_p": float(np.median([r["median_p"] for r in reps])),
                      "frac_runs_median_p_lt_0.05": float(np.mean([r["median_p"] < 0.05 for r in reps]))})
        print("curve", curve[-1])
    out["sample_size_curve"] = curve
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
