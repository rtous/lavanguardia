"""M10 same-period control: other newspapers' article-number counters (dose-response across outlets).

If a model predicts La Vanguardia's article numbers from title + date, is that specific to La Vanguardia or a general
skill with news URLs, learnable from links to any outlet? We repeat the URL test on Spanish newspapers whose URLs also
carry the date and a numeric counter, for the same periods as the LV items (members 2021-2023, controls from 2025-09).

From public Common Crawl indexes only (no site access), with light per-month prefix queries:
  1. (date, ID, URL) pairs, used to convert any predicted ID into a date (data/m10/outlet_<name>_ids.jsonl);
  2. a sample of test articles per month, whose WARC record is fetched only to read the title
     (data/m10/outlet_<name>.jsonl, with WARC provenance + SHA-256).

Usage: python -I src/m10_outlet_ids.py --outlet elperiodico|elconfidencial|elespanol [--per-month 2]
"""
import argparse, json, os, random, re, sys

sys.path.insert(0, os.path.dirname(__file__))
import trafilatura  # noqa: E402
from cc_fetch import get, fetch_record, INDEX  # noqa: E402

# per outlet: display name, host, sections, how a month is written in the URL, URL regex (section, date, id),
# and the URL prefix the model is given (up to and including the date)
OUTLETS = {
    "elperiodico": dict(name="El Periódico", host="www.elperiodico.com/es", sections=["politica", "sociedad", "internacional", "economia"],
                        month=lambda y, m: f"{y}{m:02d}", re=r"elperiodico\.com/es/([a-z\-]+)/(\d{8})/[a-z0-9\-]+-(\d{7,9})$",
                        prefix=lambda s, d: f"https://www.elperiodico.com/es/{s}/{d}/",
                        rest="las palabras clave del título separadas por guiones y el identificador numérico final"),
    "elconfidencial": dict(name="El Confidencial", host="www.elconfidencial.com", sections=["espana", "mundo", "economia"],
                           month=lambda y, m: f"{y}-{m:02d}", re=r"elconfidencial\.com/([a-z\-]+)/(\d{4}-\d{2}-\d{2})/[a-z0-9\-]+_(\d{6,8})/?$",
                           prefix=lambda s, d: f"https://www.elconfidencial.com/{s}/{d[:4]}-{d[4:6]}-{d[6:]}/",
                           rest="las palabras clave del título separadas por guiones, un guion bajo y el identificador numérico"),
    "elespanol": dict(name="El Español", host="www.elespanol.com", sections=["espana", "mundo", "economia"],
                      month=lambda y, m: f"{y}{m:02d}", re=r"elespanol\.com/([a-z\-/]+?)/(\d{8})/(?:[a-z0-9\-]+/)?(\d{7,10})_\d+\.html$",
                      prefix=lambda s, d: f"https://www.elespanol.com/{s}/{d}/",
                      rest="las palabras clave del título separadas por guiones y el identificador numérico (formato .../<ID>_0.html)"),
}
PERIODS = [(y, m) for y in (2021, 2022, 2023) for m in range(1, 13)] + [(2025, m) for m in range(9, 13)] + [(2026, m) for m in (1, 2, 3)]
CRAWL_FOR = lambda y: "CC-MAIN-2023-50" if y <= 2023 else "CC-MAIN-2026-12"


def month_pairs(o, cfg, y, m):
    rx = re.compile(cfg["re"])
    out = []
    for sec in cfg["sections"]:
        r = get(INDEX.format(crawl=CRAWL_FOR(y)), params={"url": f"{cfg['host']}/{sec}/{cfg['month'](y, m)}*", "output": "json",
                                                         "limit": 3000, "filter": ["status:200", "mime:text/html"]})
        for line in (r.text.splitlines() if r is not None else []):
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            mm = rx.search(rec.get("url", ""))
            if mm:
                d = mm.group(2).replace("-", "")
                out.append({"outlet": o, "crawl": CRAWL_FOR(y), "url": rec["url"], "section": mm.group(1), "pub_date": d,
                            "id": mm.group(3), "capture_ts": rec["timestamp"], "warc_filename": rec["filename"],
                            "warc_offset": rec["offset"], "warc_length": rec["length"]})
    return out


def title_of(r):
    raw, sha, html = fetch_record({"filename": r["warc_filename"], "offset": r["warc_offset"], "length": r["warc_length"]})
    if not html:
        return None, None
    doc = trafilatura.bare_extraction(html.decode("utf-8", "replace"), with_metadata=True)
    doc = doc if doc is None or isinstance(doc, dict) else doc.as_dict()
    t = re.sub(r"\s*[|\-–]\s*(El Peri[oó]dico|El Confidencial|El Español).*$", "", (doc or {}).get("title") or "").strip()
    return (t if len(t.split()) >= 4 else None), sha


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outlet", required=True, choices=list(OUTLETS))
    ap.add_argument("--per-month", type=int, default=2)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    o, cfg = a.outlet, OUTLETS[a.outlet]
    ids_path, test_path = f"data/m10/outlet_{o}_ids.jsonl", f"data/m10/outlet_{o}.jsonl"
    pairs = {r["id"]: r for r in map(json.loads, open(ids_path))} if os.path.exists(ids_path) else {}
    tests = {r["id"]: r for r in map(json.loads, open(test_path))} if os.path.exists(test_path) else {}
    rnd = random.Random(a.seed)
    for y, m in PERIODS:
        ym = f"{y}{m:02d}"
        if sum(r["pub_date"][:6] == ym for r in tests.values()) >= a.per_month:
            continue  # resume
        new = [r for r in month_pairs(o, cfg, y, m) if r["pub_date"][:6] == ym]
        for r in new:
            pairs.setdefault(r["id"], r)
        with open(ids_path, "w") as f:
            for r in pairs.values():
                f.write(json.dumps(r) + "\n")
        rnd.shuffle(new)
        kept = sum(r["pub_date"][:6] == ym for r in tests.values())
        with open(test_path, "a") as f:
            for r in new:
                if kept >= a.per_month:
                    break
                if r["id"] in tests:
                    continue
                t, sha = title_of(r)
                if not t:
                    continue
                rec = {**r, "title": t, "warc_record_sha256": sha, "outlet_name": cfg["name"],
                       "url_prefix": cfg["prefix"](r["section"], r["pub_date"]), "url_rest_hint": cfg["rest"]}
                tests[r["id"]] = rec
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
                kept += 1
        print(f"  {o} {ym}: {len(new)} URLs, {kept} test articles; total pairs {len(pairs)}", flush=True)


if __name__ == "__main__":
    main()
