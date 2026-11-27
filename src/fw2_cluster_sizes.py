"""How many copies of each La Vanguardia page did FineWeb-2 find? (copy count = memorization driver)

FineWeb-2 deduplicates each language globally with MinHash (near-duplicate documents across all Common Crawl dumps
2013-2024) and keeps one document per cluster, recording `minhash_cluster_size`: the number of near-identical
documents in the cluster (the kept one included). The cluster mixes repeated captures of the same page and copies on
other sites (reposts, scrapers, aggregators); both are copies a crawl-trained model could see.

Input: the FineWeb-2 hit lists from src/dataset_presence.py (shard, row_group, row of every LV document). Downloads each
shard in turn (deleted after use), reads `minhash_cluster_size` for the LV rows and checks the URL matches. Resumable.

  python -I src/fw2_cluster_sizes.py scan --lang spa_Latn [--workers 16]
  python -I src/fw2_cluster_sizes.py top --n 20    -> results/fw2_most_copied.json (+ .md)
"""
import argparse, glob, json, os, re, sys, time
from collections import defaultdict
from multiprocessing import Pool

OUT = "data/fw2_cluster_sizes"  # per-shard jsonl (large, gitignored)
ART = re.compile(r"lavanguardia\.com/(?:[\w-]+/)+(\d{8})/(\d{6,12})/[^/]+\.html")


TMP = os.environ.get("FW2_TMP", "data/fw2_tmp")  # whole shards are downloaded here one at a time, then deleted


def scan_shard(args):
    """Download one shard (a few GB), read the cluster size of the LV rows, delete the shard. Per-row-group range
    requests were rate-limited by Hugging Face (HTTP 429), so whole files are fetched instead (146 + 5 requests)."""
    shard, hits, out = args
    if os.path.exists(out):
        return shard, "skip"
    import pyarrow.parquet as pq
    from huggingface_hub import hf_hub_download
    fname = shard.split("fineweb-2/", 1)[1]
    err = None
    for attempt in range(5):
        local = None
        try:
            local = hf_hub_download("HuggingFaceFW/fineweb-2", fname, repo_type="dataset", local_dir=TMP,
                                    token=os.environ.get("HF_TOKEN"))
            pf = pq.ParquetFile(local)
            by_rg = defaultdict(list)
            for h in hits:
                by_rg[h["row_group"]].append(h)
            rows = []
            for rg, hs in sorted(by_rg.items()):
                t = pf.read_row_group(rg, columns=["minhash_cluster_size", "url"])
                col, urls = t.column(0), t.column(1)
                for h in hs:
                    assert urls[h["row"]].as_py() == h["url"], "row mismatch"
                    rows.append({"id": h["id"], "url": h["url"], "dump": h["dump"], "shard": shard, "row_group": rg,
                                 "row": h["row"], "cluster_size": col[h["row"]].as_py()})
            tmp = out + ".tmp"
            with open(tmp, "w") as f:
                f.write("".join(json.dumps(r) + "\n" for r in rows))
            os.replace(tmp, out)
            return shard, len(rows)
        except Exception as e:  # network hiccups / rate limits: back off and retry
            err = e
            time.sleep(30 * (attempt + 1))
        finally:
            if local and os.path.exists(local):
                os.remove(local)
    return shard, f"FAILED {err!r}"[:200]


def scan(lang, workers):
    hits = defaultdict(list)
    for l in open(f"results/dataset_presence_hits_{lang}.jsonl"):
        h = json.loads(l)
        hits[h["shard"]].append(h)
    os.makedirs(f"{OUT}/{lang}", exist_ok=True)
    jobs = [(s, hs, f"{OUT}/{lang}/{os.path.basename(s)}.jsonl") for s, hs in sorted(hits.items())]
    print(f"{lang}: {len(jobs)} shards, {sum(len(h) for h in hits.values())} LV documents", flush=True)
    t0 = time.time()
    with Pool(workers) as p:
        for i, (s, r) in enumerate(p.imap_unordered(scan_shard, jobs), 1):
            print(f"{i}/{len(jobs)} {os.path.basename(s)} {r} {time.time() - t0:.0f}s", flush=True)


def top(n):
    rows = [json.loads(l) for p in glob.glob(f"{OUT}/*/*.jsonl") for l in open(p)]
    lang_of = lambda r: "cat" if "cat_Latn" in r["shard"] else "spa"
    arts = [r for r in rows if ART.search(r["url"])]
    # one entry per article (an article can sit in several clusters, e.g. http/https or Catalan edition): sum them
    per = defaultdict(lambda: {"cluster_size": 0, "docs": []})
    for r in arts:
        m = ART.search(r["url"])
        k = m.group(2)
        per[k]["cluster_size"] += r["cluster_size"]
        per[k]["docs"].append({k2: r[k2] for k2 in ("url", "dump", "cluster_size", "shard", "row_group", "row")} | {"lang": lang_of(r)})
        per[k]["pub_date"] = m.group(1)
    ranked = sorted(per.items(), key=lambda kv: -kv[1]["cluster_size"])
    sizes = sorted((v["cluster_size"] for v in per.values()), reverse=True)
    q = lambda f: sizes[int(f * (len(sizes) - 1))]
    summary = {"documents_scanned": len(rows), "article_documents": len(arts), "distinct_articles": len(per),
               "cluster_size_quantiles": {"max": sizes[0], "p99.9": q(0.001), "p99": q(0.01), "p90": q(0.1), "median": q(0.5)},
               "articles_with_cluster_ge": {str(t): sum(s >= t for s in sizes) for t in (2, 5, 10, 50, 100, 500)},
               "top": [{"article_id": k, **v} for k, v in ranked[:max(n, 200)]]}
    json.dump(summary, open("results/fw2_most_copied.json", "w"), indent=1)
    print(json.dumps({k: v for k, v in summary.items() if k != "top"}, indent=1))
    for k, v in ranked[:n]:
        print(v["cluster_size"], k, v["pub_date"], v["docs"][0]["url"][:110])


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["scan", "top"])
    ap.add_argument("--lang", default="spa_Latn")
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args()
    scan(a.lang, a.workers) if a.cmd == "scan" else top(a.n)
