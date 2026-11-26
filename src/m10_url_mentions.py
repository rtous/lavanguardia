"""M10 follow-up: how available are La Vanguardia (date, ID) pairs OUTSIDE La Vanguardia's own pages?

LV article URLs contain both the publication date and the article number (/20230209/8746377/), so every written-out
LV URL anywhere is one (date, ID) example. A model can learn the date->ID counter from such mentions without reading
any LV page. This script counts written-out LV article URLs in the TEXT of FineWeb-2 documents (hyperlinks are
stripped by the extraction, so only URLs written as text remain, which is what a text-trained model sees), split by
the domain of the document that contains them (LV itself vs other sites), and by the URL's publication year.

Usage: python -I src/m10_url_mentions.py --shards 1 [--config spa_Latn]  -> results/m10_url_mentions.json
"""
import argparse, collections, json, os, random, re, time

import pyarrow.parquet as pq
from huggingface_hub import HfFileSystem

DS = "HuggingFaceFW/fineweb-2"
LV_URL = re.compile(r"lavanguardia\.com/[a-z0-9\-/]+?/(\d{4})(\d{4})/(\d{7,12})/")
LV_DOC = re.compile(r"^https?://([a-z0-9-]+\.)*lavanguardia\.com/", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default="spa_Latn")
    ap.add_argument("--shards", type=int, default=1)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    fs = HfFileSystem()
    paths = sorted(fs.glob(f"datasets/{DS}/data/{a.config}/train/*.parquet"))
    sample = sorted(random.Random(a.seed).sample(paths, a.shards))
    out = "results/m10_url_mentions.json"
    res = json.load(open(out)) if os.path.exists(out) else {"per_shard": []}
    done = {s["shard"] for s in res["per_shard"]}
    for p in sample:
        if p in done:
            continue
        t0 = time.time()
        pf = pq.ParquetFile(fs.open(p, block_size=8 * 2**20))
        rows, c = 0, collections.Counter()
        by_year = {"lv_doc": collections.Counter(), "other_doc": collections.Counter()}
        domains, examples, ids = collections.Counter(), [], set()
        for rg in range(pf.num_row_groups):
            t = pf.read_row_group(rg, columns=["url", "text"]).to_pylist()
            rows += len(t)
            for r in t:
                txt = r["text"] or ""
                if "lavanguardia.com/" not in txt:
                    continue
                ms = LV_URL.findall(txt)
                if not ms:
                    continue
                kind = "lv_doc" if LV_DOC.match(r["url"] or "") else "other_doc"
                c[kind + "_docs"] += 1
                c[kind + "_mentions"] += len(ms)
                for y, md, i in ms:
                    by_year[kind][y] += 1
                    ids.add((y + md, i))
                if kind == "other_doc":
                    domains[re.sub(r"^https?://(www\.)?([^/]+).*$", r"\2", r["url"] or "")] += 1
                    if len(examples) < 15:
                        k = txt.find("lavanguardia.com/")
                        examples.append({"doc": r["url"], "snippet": txt[max(0, k - 120):k + 120]})
            print(f"  row group {rg + 1}/{pf.num_row_groups}: {dict(c)}", flush=True)
        res["per_shard"].append({"shard": p, "rows": rows, "counts": dict(c), "distinct_date_id_pairs": len(ids),
                                 "by_year": {k: dict(sorted(v.items())) for k, v in by_year.items()},
                                 "top_other_domains": domains.most_common(25), "examples": examples,
                                 "secs": round(time.time() - t0)})
        json.dump(res, open(out, "w"), indent=1, ensure_ascii=False)
        print(res["per_shard"][-1]["counts"], "distinct pairs:", len(ids), flush=True)


if __name__ == "__main__":
    main()
