"""Dataset inference on MATCHED groups: each control is paired with a member of the same section and similar length
(live blogs excluded), so the groups differ mainly in date and exposure, not in section mix or format.

Usage: python -I src/di_matched.py results/m5_<model>.jsonl results/m5_gpt2es.jsonl --out results/di_matched_<model>.json
"""
import argparse, json, os, re, sys

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import load, features, run  # noqa: E402

LIVE = re.compile(r"^\d{1,2}:\d{2}$", re.M)


def meta(paths):
    m = {}
    for p, label in paths:
        for l in open(p, encoding="utf-8"):
            d = json.loads(l)
            m[(d["id"], label)] = {"section": d["section"].split("/")[0], "n_words": d["n_words"],
                                   "live": len(LIVE.findall(d["text"])) >= 3}
    return m


def match(mk, ck, M):
    used, pairs = set(), []
    for c in sorted(ck, key=lambda k: M[k]["n_words"]):
        cands = [k for k in mk if k not in used and M[k]["section"] == M[c]["section"]]
        if not cands:
            continue
        best = min(cands, key=lambda k: abs(M[k]["n_words"] - M[c]["n_words"]))
        if abs(M[best]["n_words"] - M[c]["n_words"]) <= 0.3 * M[c]["n_words"]:
            used.add(best); pairs.append((best, c))
    return pairs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("reference")
    ap.add_argument("--members", default="data/cc/members.jsonl")
    ap.add_argument("--controls", default="data/cc/controls.jsonl")
    ap.add_argument("--R", type=int, default=200)
    ap.add_argument("--min-member-date", default="", help="drop members published before YYYYMMDD (e.g. reference-model cutoff)")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tgt, ref = load(a.target), load(a.reference)
    if a.min_member_date:
        tgt = {k: v for k, v in tgt.items() if not (k[1] == "member" and v["pub_date"] < a.min_member_date)}
    M = meta([(a.members, "member"), (a.controls, "control")])
    keys = [k for k in sorted(set(tgt) & set(ref) & set(M)) if not M[k]["live"]]
    mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
    pairs = match(mk, ck, M)
    pm, pc = [p[0] for p in pairs], [p[1] for p in pairs]
    out = {"n_pairs": len(pairs), "excluded_live": sum(M[k]["live"] for k in M)}
    print(f"matched pairs: {len(pairs)} (live blogs excluded: {out['excluded_live']})")
    for mode in ("target", "reference", "calibrated"):
        out[mode] = run(features(tgt, ref, pm, mode), features(tgt, ref, pc, mode), a.R)
        print(f"  {mode:10s} median_p={out[mode]['median_p']:.3g} frac<0.05={out[mode]['frac_p_lt_0.05']:.2f}")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
