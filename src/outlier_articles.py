"""Which articles show more verbatim reproduction or exclusive knowledge than the rest? (exploratory, across tests)

Collects per-article maxima from M1 (continuation), M9 (sentence by sentence), M11 (NYT-style, best of 10, outside
quotes) and M10 (exclusive items: URL-number error, La Contra Q->A fact hits), and prints the top members next to the
top controls, so an outlier can be judged against what unseen articles reach by chance.
  python -I src/outlier_articles.py            -> results/outlier_articles.json
"""
import glob, json, os, re
from collections import defaultdict

def rows(p):
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]

def num(x):
    try: return float(x)
    except Exception: return None

art = defaultdict(lambda: {"set": None, "hits": []})  # id -> list of (test, model, score, text)

def add(i, s, test, model, score, text=""):
    a = art[str(i)]; a["set"] = a["set"] or s; a["hits"].append((test, model, score, text[:160]))

for p in glob.glob("results/m1_continuation_*.jsonl"):
    for r in rows(p):
        add(r["id"], r["set"], "M1" + ("-LC" if "lacontra" in p else ""), r["model"], num(r["lcs_words"]) or 0, r.get("lcs_text", ""))
for p in glob.glob("results/m9_decomposition_*.jsonl"):
    for r in rows(p):
        if str(r.get("true_in_quotes")) != "True":
            add(r["id"], r["set"], "M9", r["model"].split("/")[-1], num(r["lcs_words"]) or 0, r.get("gen", ""))
for p in glob.glob("results/m11_nyt_style_*.jsonl"):
    for r in rows(p):
        best = max((x for x in r["attempts"] if not x["lcs_in_quotes"]), key=lambda x: x["lcs_words"], default={"lcs_text": ""})
        add(r["id"], r["set"], "M11", r["model"].split("/")[-1], r["best_lcs_outside_quotes"], best.get("lcs_text", ""))

def summarize(test_filter):
    out = {}
    for s in ("member", "control"):
        best = []
        for i, a in art.items():
            if a["set"] != s: continue
            h = [x for x in a["hits"] if x[0].startswith(test_filter)]
            if h:
                top = max(h, key=lambda x: x[2]); best.append((top[2], i, top[1], top[3]))
        best.sort(reverse=True)
        out[s] = {"n": len(best), "top": best[:8]}
    return out

res = {t: summarize(t) for t in ("M1", "M9", "M11")}

# M10: URL-number error in days and Q->A hits per article (item ids are per item; keep url/answer for joining)
m10 = defaultdict(list)
for p in glob.glob("results/m10_exclusive_*.jsonl"):
    model = os.path.basename(p)[len("m10_exclusive_"):-6]
    for r in rows(p):
        if r.get("type") == "url_id" and r.get("pred") not in (None, "[]", []):
            try:
                pred = int(re.findall(r"\d+", str(r["pred"]))[0]); err = abs(pred - int(r["answer"]))
            except Exception:
                continue
            m10[("url_id", r["set"])].append((err, r["answer"], model, r["url"][:110]))
        if r.get("type") == "lacontra_qa" or r.get("subtype") == "qa":
            if str(r.get("hit")) == "True":
                m10[("qa_hit", r["set"])].append((model, r.get("url", "")[:110], str(r.get("gen", ""))[:120]))
res["M10_url_id_closest"] = {f"{k[1]}": sorted(v)[:10] for k, v in m10.items() if k[0] == "url_id"}
res["M10_qa_hits"] = {f"{k[1]}": v for k, v in m10.items() if k[0] == "qa_hit"}
# articles appearing in more than one test's top list
json.dump(res, open("results/outlier_articles.json", "w"), indent=1, ensure_ascii=False)
for t in ("M1", "M9", "M11"):
    for s in ("member", "control"):
        print(f"{t} {s} n={res[t][s]['n']}: " + "; ".join(f"{x[0]:.0f}w {x[1]} {x[2]} «{x[3][:60]}»" for x in res[t][s]["top"][:5]))
for s, v in res["M10_url_id_closest"].items():
    print("M10 url", s, [(e, a, m) for e, a, m, _ in v[:8]])
for s, v in res["M10_qa_hits"].items():
    print("M10 qa hits", s, len(v))
