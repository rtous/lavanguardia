"""Run all dataset-inference variants for every scored target model and write one summary table.

Variants per (target, reference): unmatched and matched groups; target-raw, reference-only, calibrated.
Placebo P1 (controls late-2025 vs early-2026, both unseen) on calibrated scores.
References: GPT-2-spanish (data 2018) and XGLM-2.9B (data <= 2020; members before 2020-06 dropped).

Usage: python -I src/di_summary.py   -> results/di_summary.json + printed table
"""
import json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import load, features, run  # noqa: E402
from di_matched import meta, match  # noqa: E402

TARGETS = {"Qwen2.5-7B": "qwen25_7b", "Llama-3.1-8B": "llama31_8b", "Mistral-7B-v0.3": "mistral7b_v03", "Gemma-2-9B": "gemma2_9b"}
REFS = {"GPT-2-es (2018)": ("gpt2es", ""), "XGLM-2.9B (<=2020)": ("xglm29", "20200601")}
R = 100


def analyse(tpath, rpath, min_date, M):
    tgt, ref = load(tpath), load(rpath)
    if min_date:
        tgt = {k: v for k, v in tgt.items() if not (k[1] == "member" and v["pub_date"] < min_date)}
    keys = [k for k in sorted(set(tgt) & set(ref) & set(M)) if not M[k]["live"]]
    mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
    if len(mk) < 50 or len(ck) < 50:
        return None  # scoring still in progress
    pairs = match(mk, ck, M)
    pm, pc = [p[0] for p in pairs], [p[1] for p in pairs]
    res = {"n_members": len(mk), "n_controls": len(ck), "n_pairs": len(pairs)}
    for mode in ("target", "reference", "calibrated"):
        res[f"unmatched_{mode}"] = run(features(tgt, ref, mk, mode), features(tgt, ref, ck, mode), R)["median_p"]
        res[f"matched_{mode}"] = run(features(tgt, ref, pm, mode), features(tgt, ref, pc, mode), R)["median_p"]
    old = [k for k in ck if tgt[k]["pub_date"] < "20260101"]; new = [k for k in ck if tgt[k]["pub_date"] >= "20260101"]
    res["placebo_P1_calibrated"] = run(features(tgt, ref, old, "calibrated"), features(tgt, ref, new, "calibrated"), R)["median_p"]
    return res


def main():
    M = meta([("data/cc/members.jsonl", "member"), ("data/cc/controls.jsonl", "control")])
    out = {}
    for tname, t in TARGETS.items():
        tp = f"results/m5_{t}.jsonl"
        if not os.path.exists(tp):
            continue
        for rname, (r, min_date) in REFS.items():
            rp = f"results/m5_{r}.jsonl"
            if not os.path.exists(rp):
                continue
            res = analyse(tp, rp, min_date, M)
            if res is None:
                continue
            out[f"{tname} | {rname}"] = res
            print(f"{tname:16s} {rname:20s} pairs={res['n_pairs']:3d} "
                  f"unmatched raw/ref/cal = {res['unmatched_target']:.2g}/{res['unmatched_reference']:.2g}/{res['unmatched_calibrated']:.2g}  "
                  f"matched raw/ref/cal = {res['matched_target']:.2g}/{res['matched_reference']:.2g}/{res['matched_calibrated']:.2g}  "
                  f"placebo={res['placebo_P1_calibrated']:.2g}", flush=True)
    json.dump(out, open("results/di_summary.json", "w"), indent=1)


if __name__ == "__main__":
    main()
