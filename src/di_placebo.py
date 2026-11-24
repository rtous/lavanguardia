"""Placebo tests for dataset inference: groups that differ in DATE but not in EXPOSURE.

Any 'significant' result here is a false positive produced by temporal drift alone. Running these for several time
gaps tells us how close in time the validation set must be to the suspect set.

Placebos (older group plays the role of 'suspect'):
  P1  controls Sep-Dec 2025 vs controls Jan-Mar 2026   (both UNSEEN by all target models; gap ~3-4 months)
  P2  members 2020 vs members Jul 2022-Feb 2023          (both SEEN by targets; both UNSEEN by the 2018 reference)
  P3  members 2020-2021 vs members 2022-2023             (same, wider split)
Each is run on target raw scores, reference raw scores and calibrated scores.

Usage: python -I src/di_placebo.py results/m5_qwen25_7b.jsonl results/m5_gpt2es.jsonl --out results/di_placebo_qwen25.json
"""
import argparse, json, os, sys

sys.path.insert(0, os.path.dirname(__file__))
from dataset_inference import load, features, run  # noqa: E402

PLACEBOS = {
    "P1_controls_2025Q4_vs_2026Q1": ("control", lambda d: "20250901" <= d < "20260101", lambda d: d >= "20260101"),
    "P2_members_2020_vs_2022H2-2023": ("member", lambda d: d < "20210101", lambda d: d >= "20220701"),
    "P3_members_2020-21_vs_2022-23": ("member", lambda d: d < "20220101", lambda d: d >= "20220101"),
}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target"); ap.add_argument("reference")
    ap.add_argument("--R", type=int, default=200)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tgt, ref = load(a.target), load(a.reference)
    keys = sorted(set(tgt) & set(ref))
    out = {}
    for name, (grp, f_old, f_new) in PLACEBOS.items():
        old = [k for k in keys if k[1] == grp and f_old(tgt[k]["pub_date"])]
        new = [k for k in keys if k[1] == grp and f_new(tgt[k]["pub_date"])]
        out[name] = {}
        for mode in ("target", "reference", "calibrated"):
            r = run(features(tgt, ref, old, mode), features(tgt, ref, new, mode), a.R)
            out[name][mode] = r
            print(f"{name:32s} {mode:10s} n={len(old)}/{len(new)} median_p={r['median_p']:.3g} frac<0.05={r['frac_p_lt_0.05']:.2f}")
    json.dump(out, open(a.out, "w"), indent=1)


if __name__ == "__main__":
    main()
