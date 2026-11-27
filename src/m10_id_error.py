"""Exploratory re-analysis of M10 url_id answers: error in IDs, not in days (data already seen; not pre-registered).

Question: are the near-correct IDs better than what a model could get by knowing only the date→ID pattern?
Benchmark ("date oracle"): knows the publication date exactly and guesses the ID at midday of that day, estimated by
interpolating over all OTHER articles of the corpus (leave-one-out, so the true ID is never used). LV publishes
~3,000 IDs/day, so the oracle's typical error is ~ a quarter of a day's range. A model that beats the oracle on many
articles has article-specific knowledge of the URL, not just the pattern.

  python -I src/m10_id_error.py   -> results/m10_id_error.json
"""
import glob, json, os, sys
import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m10_exclusive_facts import load_articles, _ord

THRESH = (10, 50, 200, 1000)


def main():
    pts = sorted({(int(a["id"]), _ord(a["pub_date"])) for a in load_articles() if a["id"].isdigit() and len(a["id"]) in (7, 8)})
    ids = np.array([p[0] for p in pts], float)
    days = np.array([p[1] for p in pts], float)

    def oracle(true_id, pub_date):
        keep = ids != true_id  # leave the target article out
        d, i = days[keep], ids[keep]
        o = np.argsort(d, kind="stable")
        d, i = d[o], np.maximum.accumulate(i[o])
        return float(np.interp(_ord(pub_date) + 0.5, d, i))

    out = {}
    for path in sorted(glob.glob("results/m10_exclusive_*.jsonl")):
        name = os.path.basename(path)[len("m10_exclusive_"):-len(".jsonl")]
        rows = [r for r in map(json.loads, open(path)) if r["type"] == "url_id" and not r.get("subtype")
                and not r.get("api_error") and len(r["answer"]) in (7, 8)]
        if not rows:
            continue
        res = {}
        for st in ("member", "control"):
            err, orc, ex = [], [], []
            for r in (x for x in rows if x["set"] == st):
                t = int(r["answer"])
                pub = r["url"].split("/")[4]
                same_len = [int(p) for p in r["pred"] if len(p) == len(r["answer"])]
                e = min((abs(p - t) for p in same_len), default=None)
                oe = abs(oracle(t, pub) - t)
                err.append(e)
                orc.append(oe)
                if e is not None and e <= 50:
                    ex.append({"url": r["url"], "true": t, "pred": same_len, "err_ids": e, "oracle_err_ids": round(oe)})
            n = len(err)
            valid = [e for e in err if e is not None]
            beats = sum(1 for e, o in zip(err, orc) if e is not None and e < o)
            res[st] = {"n": n, "answered": len(valid),
                       "median_err_ids": float(np.median(valid)) if valid else None,
                       "oracle_median_err_ids": float(np.median(orc)) if orc else None,
                       **{f"within_{k}": sum(e <= k for e in valid) for k in THRESH},
                       **{f"oracle_within_{k}": sum(o <= k for o in orc) for k in THRESH},
                       "beats_date_oracle": beats, "examples_within_50": ex}
        out[name] = res
        m, c = res["member"], res["control"]
        print(f"{name:38s} member n={m['n']:3d} med={m['median_err_ids']}  ≤50: {m['within_50']} (oracle {m['oracle_within_50']})"
              f"  ≤200: {m['within_200']} (oracle {m['oracle_within_200']})  beats oracle: {m['beats_date_oracle']}"
              f" | control n={c['n']} ≤200: {c['within_200']} (oracle {c['oracle_within_200']})")
    with open("results/m10_id_error.json", "w") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)


if __name__ == "__main__":
    main()
