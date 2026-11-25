"""Which of our evaluation articles are inside FineWeb-2? Matches article ids (URL path /YYYYMMDD/<id>/) between the
evaluation sets (data/cc/*.jsonl) and the FineWeb-2 hits of src/dataset_presence.py. Also reports the share of the
dataset scanned, so a partial scan can be read as a sample (expected hit share if every article were present).

Usage: python -I src/presence_overlap.py  -> results/dataset_presence_overlap.json
"""
import json, re

P = json.load(open("results/dataset_presence.json"))
ids = {}
for c in P:
    for l in open(f"results/dataset_presence_hits_{c}.jsonl", encoding="utf-8"):
        r = json.loads(l)
        m = re.search(r"/\d{8}/(\d+)/", r["url"])
        if m:
            ids.setdefault(m.group(1), []).append({"config": c, "fineweb_id": r["id"], "dump": r["dump"], "url": r["url"]})
frac = {c: v["n_shards_scanned"] / v["n_shards_total"] for c, v in P.items()}
out = {"scanned_fraction": frac, "sets": {}}
for f in ("members", "mid2023", "controls", "lacontra_members", "lacontra_controls"):
    docs = [json.loads(l) for l in open(f"data/cc/{f}.jsonl", encoding="utf-8")]
    hit = {d["id"]: ids[d["id"]] for d in docs if d["id"] in ids}
    out["sets"][f] = {"n": len(docs), "found": len(hit), "share": round(len(hit) / len(docs), 4), "hits": hit}
    print(f, len(docs), len(hit), round(len(hit) / len(docs), 3))
print("scanned fraction", frac)
json.dump(out, open("results/dataset_presence_overlap.json", "w"), indent=1, ensure_ascii=False)
