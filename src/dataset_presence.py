"""Supporting fact: are lavanguardia.com pages inside public, documented LLM *pretraining datasets*?

Reads only the `url` / `dump` / `date` / `id` columns of parquet shards of HuggingFaceFW/fineweb-2 (Spanish and
Catalan configs) over HTTP range requests (column projection, no full download), counts rows whose URL is on
lavanguardia.com, and extrapolates from the sampled shards to the whole config. For a few hits it also fetches the
text, so the record can be compared with the article. Output: results/dataset_presence.json (+ hits list).

Usage: python -I src/dataset_presence.py --config spa_Latn --shards 6 [--seed 0]   (resumable; --shards 999 = all)
"""
import argparse, json, os, random, re, time

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

DS = "HuggingFaceFW/fineweb-2"
PAT = re.compile(r"^https?://([a-z0-9-]+\.)*lavanguardia\.com/", re.I)


def scan(fs, path, n_text=3):
    pf = pq.ParquetFile(fs.open(path, block_size=8 * 2**20))
    rows, hits = 0, []
    for rg in range(pf.num_row_groups):
        t = pf.read_row_group(rg, columns=["id", "url", "dump", "date"]).to_pylist()
        rows += len(t)
        for i, r in enumerate(t):
            if PAT.match(r["url"] or ""):
                hits.append({**r, "row_group": rg, "row": i})
    for h in hits[:n_text]:  # fetch text for a few hits, as an exhibit
        txt = pf.read_row_group(h["row_group"], columns=["text"]).column("text")[h["row"]].as_py()
        h["text_head"] = txt[:600]
    return rows, hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="spa_Latn")
    ap.add_argument("--shards", type=int, default=6)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="results/dataset_presence.json")
    a = ap.parse_args()
    fs = HfFileSystem()
    files = fs.glob(f"datasets/{DS}/data/{a.config}/train/*.parquet", detail=True)
    paths = sorted(files)
    sample = sorted(random.Random(a.seed).sample(paths, min(a.shards, len(paths))))
    res = json.load(open(a.out)) if os.path.exists(a.out) else {}
    per = list(res.get(a.config, {}).get("per_shard", []))  # resume: keep shards already scanned
    seen = {x["shard"] for x in per}
    for p in sample:
        if p in seen:
            continue
        t0 = time.time()
        rows, hits = scan(fs, p)
        per.append({"shard": p, "bytes": files[p]["size"], "rows": rows, "hits": len(hits), "secs": round(time.time() - t0)})
        print(per[-1], flush=True)
        with open(a.out.replace(".json", f"_hits_{a.config}.jsonl"), "a") as f:
            for h in hits:
                f.write(json.dumps({"shard": p, **h}, ensure_ascii=False) + "\n")
        _save(res, a, per, files, paths)  # after the hits, so a crash never marks a shard done without them
    _save(res, a, per, files, paths)
    print({k: v for k, v in res[a.config].items() if k != "per_shard"})


def _save(res, a, per, files, paths):
    tot_bytes = sum(v["size"] for v in files.values())
    s_rows, s_hits, s_bytes = (sum(x[k] for x in per) for k in ("rows", "hits", "bytes"))
    res[a.config] = {"dataset": DS, "config": a.config, "n_shards_total": len(paths), "n_shards_scanned": len(per),
                     "rows_scanned": s_rows, "hits_scanned": s_hits, "hit_rate": s_hits / max(1, s_rows),
                     "est_total_hits": round(s_hits * tot_bytes / max(1, s_bytes)), "per_shard": per,
                     "scanned_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "seed": a.seed}
    json.dump(res, open(a.out + ".tmp", "w"), indent=1)
    os.replace(a.out + ".tmp", a.out)


if __name__ == "__main__":
    main()
