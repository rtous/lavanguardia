"""Fetch La Vanguardia articles from Common Crawl (public, legal source) with provenance.

Usage:
  python -I src/cc_fetch.py --crawl CC-MAIN-2023-14 --sections politica,opinion --months 2022-01:2022-12 \
      --per-month 3 --out data/cc/members.jsonl

For each kept article it writes one JSON line with: url, crawl id, capture timestamp, WARC filename/offset/length
(so anyone can re-download the exact same bytes from Common Crawl), SHA-256 of the raw WARC record,
extracted title/author/body text, and the filter decisions.

Filters (to keep only *exclusive, signed* La Vanguardia journalism):
  - article URL shape /section/YYYYMMDD/<id>/<slug>.html
  - Spanish or Catalan text (stopword ratio), >= MIN_WORDS words
  - non-empty byline, not a news agency (EFE, Europa Press, ACN, Reuters, AFP, AP, "Agencias", "Redacción")
  - no agency marker in the body
"""
import argparse, concurrent.futures as cf, hashlib, io, json, os, re, sys, time

import requests
import trafilatura
from warcio.archiveiterator import ArchiveIterator

INDEX = "https://index.commoncrawl.org/{crawl}-index"
DATA = "https://data.commoncrawl.org/"
UA = {"User-Agent": "research-provenance-check/0.1"}
ARTICLE_RE = re.compile(r"lavanguardia\.com/([a-z0-9\-/]+)/(\d{8})/(\d+)/[^/]+\.html$")
MIN_WORDS = 300
AGENCY_RE = re.compile(r"\b(efe|europa press|acn|reuters|afp|associated press|agencias?|redacci[oó]n|lavanguardia\.com|servimedia|colpisa|ep)\b", re.I)
BODY_AGENCY_RE = re.compile(r"\((?:efe|ep|acn|afp|reuters|europa press)\)|\b(?:efe|europa press|acn)\s*[\.\-–—]|\bagencia efe\b", re.I)
ES_SW = set("de la que el en y a los del se las por un para con no una su al lo como más pero sus le ya o este sí porque esta entre cuando muy sin sobre también me hasta hay donde quien desde todo nos durante todos uno les ni contra otros ese eso ante ellos e esto mí antes algunos qué unos yo otro otras otra él tanto esa estos mucho quienes nada muchos cual poco ella estar estas algunas algo nosotros".split())
CA_SW = set("de la que el i a els del es les per un una amb no seu al com més però ja o aquest sí perquè aquesta entre quan molt sense sobre també fins hi ha on qui des de tot ens durant tots als dels pel pels".split())


def get(url, tries=6, **kw):
    hdr = {**UA, **kw.pop("headers", {})}
    for attempt in range(tries):
        try:
            r = requests.get(url, headers=hdr, timeout=120, **kw)
            if r.status_code == 404 and "index.commoncrawl" in url:
                return None  # "No Captures found"
            if r.status_code in (429, 500, 502, 503, 504):
                raise requests.HTTPError(r.status_code)
            r.raise_for_status()
            return r
        except Exception as e:
            wait = 5 * (attempt + 1)
            print(f"  retry {attempt+1} ({e}); sleeping {wait}s", file=sys.stderr)
            time.sleep(wait)
    print(f"  GAVE UP: {url}", file=sys.stderr)
    return None


def query_index(crawl, pattern, limit):
    r = get(INDEX.format(crawl=crawl), params={"url": pattern, "output": "json", "limit": limit,
                                               "filter": ["status:200", "mime:text/html"]})
    if r is None:
        return []
    out, seen = [], set()
    for line in r.text.splitlines():
        try:
            rec = json.loads(line)
        except json.JSONDecodeError:
            continue
        m = ARTICLE_RE.search(rec.get("url", ""))
        if m and m.group(3) not in seen:
            seen.add(m.group(3))
            out.append(rec)
    return out


def fetch_record(rec):
    off, length = int(rec["offset"]), int(rec["length"])
    r = get(DATA + rec["filename"], headers={"Range": f"bytes={off}-{off+length-1}"})
    if r is None:
        return None, None, None
    raw = r.content
    sha = hashlib.sha256(raw).hexdigest()
    for record in ArchiveIterator(io.BytesIO(raw)):
        if record.rec_type == "response":
            return raw, sha, record.content_stream().read()
    return raw, sha, None


def language(text):
    w = re.findall(r"[a-záéíóúñçàèòïü·]+", text.lower())[:400]
    if not w:
        return None, 0.0
    es = sum(x in ES_SW for x in w) / len(w)
    ca = sum(x in CA_SW for x in w) / len(w)
    if max(es, ca) < 0.15:
        return None, max(es, ca)
    return ("ca" if ca > es else "es"), max(es, ca)


def process(rec, crawl):
    raw, sha, html = fetch_record(rec)
    if not html:
        return None, "no_html"
    doc = trafilatura.bare_extraction(html.decode("utf-8", "replace"), with_metadata=True, include_comments=False)
    if doc is None:
        return None, "no_extract"
    doc = doc if isinstance(doc, dict) else doc.as_dict()
    text, author = doc.get("text") or "", (doc.get("author") or "").strip()
    nw = len(text.split())
    lang, score = language(text)
    if lang is None:
        return None, "language"
    if nw < MIN_WORDS:
        return None, "short"
    if not author:
        return None, "no_byline"
    if AGENCY_RE.search(author):
        return None, "agency_byline"
    if BODY_AGENCY_RE.search(text[:400]) or BODY_AGENCY_RE.search(text[-300:]):
        return None, "agency_body"
    m = ARTICLE_RE.search(rec["url"])
    return {
        "id": m.group(3), "url": rec["url"], "section": m.group(1), "pub_date": m.group(2),
        "crawl": crawl, "capture_ts": rec["timestamp"],
        "warc_filename": rec["filename"], "warc_offset": rec["offset"], "warc_length": rec["length"],
        "warc_record_sha256": sha, "title": doc.get("title"), "author": author, "lang": lang,
        "n_words": nw, "text": text,
    }, "kept"


def months(spec):
    a, b = spec.split(":")
    y, m = map(int, a.split("-"))
    y2, m2 = map(int, b.split("-"))
    while (y, m) <= (y2, m2):
        yield f"{y:04d}{m:02d}"
        m += 1
        if m == 13:
            y, m = y + 1, 1


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crawl", required=True)
    ap.add_argument("--sections", required=True, help="comma list, e.g. politica,opinion,internacional")
    ap.add_argument("--months", required=True, help="YYYY-MM:YYYY-MM (publication months, from URL)")
    ap.add_argument("--per-month", type=int, default=2, help="kept articles per section per month")
    ap.add_argument("--out", required=True)
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--index-limit", type=int, default=3000)
    a = ap.parse_args()

    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    have = set()
    if os.path.exists(a.out):
        have = {json.loads(l)["id"] for l in open(a.out, encoding="utf-8")}
    stats = {}
    with open(a.out, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for sec in a.sections.split(","):
            for yr in sorted({m[:4] for m in months(a.months)}):
                wanted = {m for m in months(a.months) if m.startswith(yr)}
                recs = [r for r in query_index(a.crawl, f"www.lavanguardia.com/{sec}/{yr}*", a.index_limit)
                        if ARTICLE_RE.search(r["url"]).group(2)[:6] in wanted
                        and ARTICLE_RE.search(r["url"]).group(3) not in have]
                by_month = {}
                for r in recs:
                    by_month.setdefault(ARTICLE_RE.search(r["url"]).group(2)[:6], []).append(r)
                # round-robin over months so the sample is spread in time
                queue, i = [], 0
                while any(by_month.values()):
                    for m in sorted(by_month):
                        if by_month[m]:
                            queue.append(by_month[m].pop(0))
                kept_m = {}
                for i in range(0, len(queue), a.workers):
                    batch = [r for r in queue[i:i + a.workers]
                             if kept_m.get(ARTICLE_RE.search(r["url"]).group(2)[:6], 0) < a.per_month]
                    if not batch:
                        continue
                    for res, why in ex.map(lambda r: process(r, a.crawl), batch):
                        stats[why] = stats.get(why, 0) + 1
                        if res and res["id"] not in have and kept_m.get(res["pub_date"][:6], 0) < a.per_month:
                            f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
                            have.add(res["id"]); kept_m[res["pub_date"][:6]] = kept_m.get(res["pub_date"][:6], 0) + 1
                print(f"{a.crawl} {sec} {yr}: kept {sum(kept_m.values())} (candidates {len(recs)}) stats={stats}", flush=True)
    print(f"done -> {a.out}; filter stats: {stats}")


if __name__ == "__main__":
    main()
