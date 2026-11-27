"""Check the text of the most-copied LV pages (results/fw2_most_copied.json) and drop non-articles (error pages,
stubs). Reads each kept document from FineWeb-2 (whole shard download, deleted after). Writes
results/fw2_most_copied_checked.json (no article text; text goes to data/fw2_top_text.json, gitignored) and .md.
  python -I src/fw2_top_check.py --check 30 --n 20
"""
import argparse, json, os
from collections import defaultdict
import pyarrow.parquet as pq
from huggingface_hub import hf_hub_download

TMP = os.environ.get("FW2_TMP", "/content/fw2_tmp")
ERR = ("¿QUÉ HA PASADO?", "Puede que se haya renombrado o movido la página")

def main(check, n):
    s = json.load(open("results/fw2_most_copied.json"))
    cand = s["top"][:check]
    by_shard = defaultdict(list)
    for t in cand:
        d = max(t["docs"], key=lambda d: d["cluster_size"])
        by_shard[d["shard"]].append((t, d))
    texts = {}
    for shard, items in sorted(by_shard.items()):
        f = hf_hub_download("HuggingFaceFW/fineweb-2", shard.split("fineweb-2/", 1)[1], repo_type="dataset",
                            local_dir=TMP, token=os.environ.get("HF_TOKEN"))
        pf = pq.ParquetFile(f)
        for t, d in items:
            r = pf.read_row_group(d["row_group"], columns=["url", "text"])
            assert r.column(0)[d["row"]].as_py() == d["url"], "row mismatch"
            texts[t["article_id"]] = r.column(1)[d["row"]].as_py()
        os.remove(f)
        print("read", os.path.basename(shard), flush=True)
    rows = []
    for t in cand:
        txt = texts[t["article_id"]]
        words = len(txt.split())
        kind = "error page" if any(e in txt for e in ERR) else ("stub" if words < 100 else "article")
        d = max(t["docs"], key=lambda d: d["cluster_size"])
        rows.append({"article_id": t["article_id"], "pub_date": t["pub_date"], "copies": t["cluster_size"],
                     "url": d["url"], "section": d["url"].split("lavanguardia.com/")[1].split("/")[0],
                     "words": words, "kind": kind, "first_words": " ".join(txt.split()[:25])})
    ok = [r for r in rows if r["kind"] == "article"][:n]
    json.dump({"checked": rows, "top": ok}, open("results/fw2_most_copied_checked.json", "w"), ensure_ascii=False, indent=1)
    json.dump(texts, open("data/fw2_top_text.json", "w"), ensure_ascii=False)
    md = ["# The 20 most-copied La Vanguardia articles in FineWeb-2", "",
          "Copies = FineWeb-2 `minhash_cluster_size`: near-identical documents found across Common Crawl 2013-2024 "
          "(repeat captures of the page plus copies on other sites), summed over the article's kept documents. "
          "Non-articles (error pages, stubs) removed after reading the text. Source: src/fw2_cluster_sizes.py, src/fw2_top_check.py.", "",
          "| # | Copies | Date | Section | Words | URL |", "|---|---|---|---|---|---|"]
    for i, r in enumerate(ok, 1):
        md.append(f"| {i} | {r['copies']} | {r['pub_date'][:4]}-{r['pub_date'][4:6]}-{r['pub_date'][6:]} | {r['section']} | {r['words']} | {r['url']} |")
    dropped = [r for r in rows if r["kind"] != "article"]
    md += ["", "Dropped: " + ("; ".join(f"{r['url']} ({r['kind']}, {r['copies']})" for r in dropped) or "none")]
    open("results/fw2_most_copied.md", "w").write("\n".join(md) + "\n")
    print("\n".join(md))

if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("--check", type=int, default=30); ap.add_argument("--n", type=int, default=20)
    a = ap.parse_args(); main(a.check, a.n)
