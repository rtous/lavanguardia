"""Robustness of a matched+calibrated dataset-inference result: vary match tolerance, use single features,
and drop one section at a time. A real training signal should survive all of them.

Usage: python -I src/di_robust.py results/m5_gemma2_9b.jsonl results/m5_gpt2es.jsonl --out results/di_robust_gemma2_9b.json
"""
import argparse, json, os, sys
from collections import Counter

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import load, features, run, FEATS  # noqa: E402
from di_matched import meta  # noqa: E402


def match(mk, ck, M, tol):
    used, pairs = set(), []
    for c in sorted(ck, key=lambda k: M[k]["n_words"]):
        cands = [k for k in mk if k not in used and M[k]["section"] == M[c]["section"]]
        if not cands:
            continue
        best = min(cands, key=lambda k: abs(M[k]["n_words"] - M[c]["n_words"]))
        if abs(M[best]["n_words"] - M[c]["n_words"]) <= tol * M[c]["n_words"]:
            used.add(best); pairs.append((best, c))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("reference")
    ap.add_argument("--min-member-date", default="")
    ap.add_argument("--R", type=int, default=100)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tgt, ref = load(a.target), load(a.reference)
    if a.min_member_date:
        tgt = {k: v for k, v in tgt.items() if not (k[1] == "member" and v["pub_date"] < a.min_member_date)}
    M = meta([("data/cc/members.jsonl", "member"), ("data/cc/controls.jsonl", "control")])
    keys = [k for k in sorted(set(tgt) & set(ref) & set(M)) if not M[k]["live"]]
    mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
    out = {"tolerance": {}, "single_feature": {}, "drop_section": {}}
    for tol in (0.1, 0.2, 0.3, 0.5):
        p = match(mk, ck, M, tol)
        r = run(features(tgt, ref, [x[0] for x in p], "calibrated"), features(tgt, ref, [x[1] for x in p], "calibrated"), a.R)
        out["tolerance"][tol] = {"n_pairs": len(p), "median_p": r["median_p"]}
        print(f"tol={tol}: pairs={len(p)} p={r['median_p']:.3g}", flush=True)
    pairs = match(mk, ck, M, 0.3)
    pm, pc = [x[0] for x in pairs], [x[1] for x in pairs]
    Xm, Xc = features(tgt, ref, pm, "calibrated"), features(tgt, ref, pc, "calibrated")
    for j, f in enumerate(FEATS):
        r = run(Xm[:, [j]], Xc[:, [j]], a.R)
        out["single_feature"][f] = r["median_p"]
        print(f"feature {f}: p={r['median_p']:.3g}  mean member-control={Xm[:, j].mean() - Xc[:, j].mean():+.4f}", flush=True)
    secs = Counter(M[c]["section"] for c in pc)
    for s, n in secs.most_common(6):
        keep = [i for i, c in enumerate(pc) if M[c]["section"] != s]
        r = run(Xm[keep], Xc[keep], a.R)
        out["drop_section"][s] = {"n_pairs": len(keep), "median_p": r["median_p"]}
        print(f"drop {s} ({n}): pairs={len(keep)} p={r['median_p']:.3g}", flush=True)
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
