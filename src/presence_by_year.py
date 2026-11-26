"""Aggregate the FineWeb-2 hit lists (src/dataset_presence.py) by Common Crawl year and by article publication year.

The hit lists (results/dataset_presence_hits_<config>.jsonl, ~65 MB, not in git) hold one row per lavanguardia.com
document with its FineWeb-2 id, URL and source crawl. Publication year = the YYYYMMDD in the article URL; documents
without one (section fronts, tags, hemeroteca pages) are counted as "no date".
Output: results/dataset_presence_by_year.json (small, in git; used by paper/make_fig_presence.py).
Usage: python -I src/presence_by_year.py
"""
import json, re
from collections import Counter

out = {}
for c in ("spa_Latn", "cat_Latn"):
    crawl, pub, n, urls = Counter(), Counter(), 0, set()
    for l in open(f"results/dataset_presence_hits_{c}.jsonl", encoding="utf-8"):
        r = json.loads(l); n += 1; urls.add(r["url"])
        crawl[r["dump"][8:12]] += 1
        m = re.search(r"/((?:19|20)\d\d)[01]\d[0-3]\d/\d+/", r["url"])
        pub[m.group(1) if m else "no date"] += 1
    out[c] = {"documents": n, "distinct_urls": len(urls), "by_crawl_year": dict(sorted(crawl.items())),
              "by_publication_year": dict(sorted(pub.items()))}
json.dump(out, open("results/dataset_presence_by_year.json", "w"), indent=1)
print(json.dumps(out, indent=1))
