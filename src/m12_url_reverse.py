"""M12: reverse URL test. Given a La Vanguardia URL with its numeric ID but WITHOUT the title words (slug), can the
model say which article it is? Pre-registered: docs/prereg/m12_url_reverse.md.

Why: M10 found Gemini predicts LV article IDs to within days. One explanation: it estimates between IDs it saw on
third-party pages. Another: it saw LV pages together with their URLs. Only the second lets a model go from an ID
back to a specific article.

Design (built-in control): articles come in PAIRS with the same publication date and section. Both are queried.
Each answer is scored against its own title and against the partner's title. A model that uses only the date and
section cannot tell the two apart, so the pair score is 0 on average by construction. A positive score means the ID
itself identifies the article. Post-cutoff controls (published after the model's training data) are run the same way.

Usage:
  python -I src/m12_url_reverse.py build                         -> data/m12/pairs.jsonl (deterministic; sha256 printed)
  python -I src/m12_url_reverse.py run --model gemini-3.5-flash-lite
  python -I src/m12_url_reverse.py summary                       -> results/m12_url_reverse_summary.json
  python -I src/m12_url_reverse.py run --model ... --rerun       -> chain-of-custody re-run (docs/evidence_gaps.md):
      same prompts/params, results in results/rerun_custody/, raw records in evidence/m12_url_reverse_rerun/
  python -I src/m12_url_reverse.py compare                       -> results/rerun_custody/m12_compare.json
"""
import argparse, glob, hashlib, json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m10_exclusive_facts import ITEMS, norm  # same article pool and normalisation as M10 url_id

EXP = "m12_url_reverse"
PAIRS = "data/m12/pairs.jsonl"
STOP = set("""el la los las un una unos unas de del al a en y e o u que por para con sin sobre entre tras ante bajo
desde hasta hacia contra segun su sus se lo le les es son fue ser ha han hay mas muy ya no si como pero sino este esta
estos estas ese esa eso aquel nos me te mi tu yo nuestro nuestra cuando donde quien cual qui que dels les els i amb per
una uns""".split())


def content_words(s):
    return {t for t in norm(s).split() if len(t) >= 4 and t not in STOP and not t.isdigit()}


def overlap(pred, title, section):
    """Share of the title's content words that appear in the prediction (section name excluded: it is in the prompt)."""
    tw = content_words(title) - {norm(section)}
    return len(tw & content_words(pred)) / len(tw) if tw else None


def build():
    items = [json.loads(l) for l in open(ITEMS, encoding="utf-8")]
    u = [i for i in items if i["type"] == "url_id" and not i.get("subtype")]  # LV only, file order (seeded shuffle)
    groups = defaultdict(list)
    for i in u:
        groups[(i["set"], i["pub_date"], i["section"])].append(i)
    pairs = []
    for (st, d, sec), g in groups.items():
        g = sorted(g, key=lambda x: int(x["article_id"]))  # deterministic: two lowest IDs of the day and section
        if len(g) >= 2 and content_words(g[0]["title"]) and content_words(g[1]["title"]):
            a, b = g[0], g[1]
            pid = hashlib.sha256(f"{a['url']}|{b['url']}".encode()).hexdigest()[:12]
            pairs.append({"pair_id": pid, "set": st, "pub_date": d, "section": sec,
                          "a": {k: a[k] for k in ("url", "article_id", "title")},
                          "b": {k: b[k] for k in ("url", "article_id", "title")}})
    pairs.sort(key=lambda p: (p["set"], p["pub_date"], p["section"]))
    os.makedirs(os.path.dirname(PAIRS), exist_ok=True)
    with open(PAIRS, "w", encoding="utf-8") as f:
        for p in pairs:
            f.write(json.dumps(p, ensure_ascii=False) + "\n")
    for st in ("member", "control"):
        print(st, sum(p["set"] == st for p in pairs), "pairs")
    print("sha256:", hashlib.sha256(open(PAIRS, "rb").read()).hexdigest())


PILOT_PAIRS = {"09155a565d23"}  # control pair whose v2 answers were the pilot (amendment 1): not analysed
PROMPT_VERSION = 2  # v1 (2 control queries, pilot) asked to "look up" the URL and got "I cannot browse" refusals


def prompt(p, x):
    from m10_exclusive_facts import hdate
    url = f"https://www.lavanguardia.com/{p['section']}/{p['pub_date']}/{x['article_id']}/"
    return (f"No hace falta que accedas a internet: responde de memoria. El artículo de La Vanguardia con el número "
            f"{x['article_id']}, publicado el {hdate(p['pub_date'])} en la sección «{p['section']}», tiene una URL que empieza "
            f"por {url}\n¿Cuál es su titular? Responde solo con el titular, sin explicaciones. "
            "Si no estás seguro, da igualmente tu mejor suposición.")


RERUN_DIR = os.environ.get("RERUN_DIR", "results/rerun_custody")  # custody re-run 2: results/rerun_custody2
RERUN_SUFFIX = os.environ.get("RERUN_SUFFIX", "_rerun")  # evidence/<exp><suffix>/


def out_path(model, rerun=False):
    return f"{RERUN_DIR if rerun else 'results'}/m12_url_reverse_{model.split('/')[-1]}.jsonl"


def run(model, limit, rerun=False):
    from probe import ask
    pairs = [json.loads(l) for l in open(PAIRS, encoding="utf-8")]
    out = out_path(model, rerun)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    exp = EXP + RERUN_SUFFIX if rerun else EXP
    done = set()
    if os.path.exists(out):
        done = {(r["pair_id"], r["side"]) for r in map(json.loads, open(out))
                if not r.get("api_error") and r.get("prompt_version", 1) == PROMPT_VERSION}
    todo = [(p, s) for p in pairs for s in ("a", "b") if (p["pair_id"], s) not in done][:limit or None]
    print(f"{model}: {len(todo)} queries to run", flush=True)
    with open(out, "a", encoding="utf-8") as f:
        for i, (p, s) in enumerate(todo):
            x, y = p[s], p["b" if s == "a" else "a"]
            q = prompt(p, x)
            text, rec = ask(exp, model, q, max_tokens=100,
                            meta={"pair_id": p["pair_id"], "side": s, "set": p["set"], "url": x["url"]})
            err = rec["stop_reason"] == "api_error"
            r = {"pair_id": p["pair_id"], "side": s, "set": p["set"], "pub_date": p["pub_date"], "section": p["section"],
                 "url": x["url"], "title": x["title"], "partner_title": y["title"], "model": model,
                 "model_reported": rec["model_reported"], "prompt": q, "gen": text, "evidence_sha256": rec["sha256"],
                 "api_error": err, "prompt_version": PROMPT_VERSION, "ov_own": overlap(text, x["title"], p["section"]),
                 "ov_partner": overlap(text, y["title"], p["section"])}
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            f.flush()
            if err:
                print("  api error:", str(rec["response"])[:200], flush=True)
                if "per day" in str(rec["response"]).lower() or "limit: 0" in str(rec["response"]):
                    print("  daily quota reached; rerun tomorrow (resumes)", flush=True)
                    break
            elif (r["ov_own"] or 0) >= 0.5:
                print(f"  [{p['set']}] own {r['ov_own']:.2f} partner {r['ov_partner']:.2f}: {x['title'][:60]!r} <- {text[:60]!r}", flush=True)
            if i % 50 == 49:
                print(f"  {i + 1}/{len(todo)}", flush=True)


def summary(src_dir="results", out="results/m12_url_reverse_summary.json"):
    from scipy.stats import wilcoxon, mannwhitneyu, fisher_exact
    tab = {}
    for path in sorted(glob.glob(f"{src_dir}/m12_url_reverse_*.jsonl")):
        if path.endswith("_summary.json"):
            continue
        rows = {}
        for r in map(json.loads, open(path)):
            if not r["api_error"] and r.get("prompt_version", 1) == PROMPT_VERSION and r["pair_id"] not in PILOT_PAIRS:
                rows[(r["pair_id"], r["side"])] = r  # last valid answer per query
        by = defaultdict(dict)
        for (pid, s), r in rows.items():
            by[pid][s] = r
        res = {}
        for st in ("member", "control"):
            d, ex = [], 0
            for pid, sides in by.items():
                if len(sides) < 2 or sides["a"]["set"] != st or None in (sides["a"]["ov_own"], sides["b"]["ov_own"]):
                    continue
                d.append(sum(sides[s]["ov_own"] - sides[s]["ov_partner"] for s in "ab") / 2)
            singles = [r for r in rows.values() if r["set"] == st and r["ov_own"] is not None]
            ex = sum(r["ov_own"] >= 0.8 for r in singles)
            p = wilcoxon(d, alternative="greater").pvalue if any(d) else 1.0
            res[st] = {"pairs": len(d), "mean_pair_score": round(sum(d) / len(d), 4) if d else None,
                       "pairs_positive": sum(x > 0 for x in d), "pairs_negative": sum(x < 0 for x in d),
                       "wilcoxon_p_greater": p, "queries": len(singles), "title_overlap_ge_0.8": ex, "_d": d}
        m, c = res["member"], res["control"]
        if m["_d"] and c["_d"]:
            res["member_vs_control_mw_p"] = mannwhitneyu(m["_d"], c["_d"], alternative="greater").pvalue
            res["overlap_ge_0.8_fisher_p"] = fisher_exact([[m["title_overlap_ge_0.8"], m["queries"] - m["title_overlap_ge_0.8"]],
                                                           [c["title_overlap_ge_0.8"], c["queries"] - c["title_overlap_ge_0.8"]]],
                                                          alternative="greater")[1]
        for st in ("member", "control"):
            res[st].pop("_d")
        name = os.path.basename(path)[len("m12_url_reverse_"):-len(".jsonl")]
        tab[name] = res
        print(name, json.dumps(res, indent=1))
    with open(out, "w") as f:
        json.dump(tab, f, indent=1)


def compare():
    """Run 1 vs chain-of-custody re-run: identical answers, and the pre-registered statistics on each run."""
    import contextlib, io
    res = {}
    for p2 in sorted(glob.glob(f"{RERUN_DIR}/m12_url_reverse_*.jsonl")):
        p1 = "results/" + os.path.basename(p2)
        key = lambda r: (r["pair_id"], r["side"])
        last = lambda p: {key(r): r for r in map(json.loads, open(p)) if r.get("prompt_version", 1) == PROMPT_VERSION
                          and not r.get("api_error")}
        r1, r2 = last(p1), last(p2)
        both = sorted(set(r1) & set(r2))
        same = sum(r1[k]["gen"].strip() == r2[k]["gen"].strip() for k in both)
        same_norm = sum(norm(r1[k]["gen"]) == norm(r2[k]["gen"]) for k in both)
        sc = lambda r: (r["ov_own"] or 0) - (r["ov_partner"] or 0)
        res[os.path.basename(p2)] = {"n_run1": len(r1), "n_rerun": len(r2), "n_both": len(both),
                                     "identical_text": same, "identical_normalised": same_norm,
                                     "same_pair_side_score": sum(abs(sc(r1[k]) - sc(r2[k])) < 1e-9 for k in both)}
    # pre-registered summary on the re-run files (temporarily point the glob at them)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        summary(src_dir=RERUN_DIR, out=f"{RERUN_DIR}/m12_url_reverse_summary_rerun.json")
    res["rerun_summary_file"] = f"{RERUN_DIR}/m12_url_reverse_summary_rerun.json"
    print(json.dumps(res, indent=1))
    json.dump(res, open(f"{RERUN_DIR}/m12_compare.json", "w"), indent=1)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["build", "run", "summary", "compare"])
    ap.add_argument("--model", default="gemini-3.5-flash-lite")
    ap.add_argument("--limit", type=int, default=0, help="max queries this call (0 = all)")
    ap.add_argument("--rerun", action="store_true", help="chain-of-custody re-run (separate results + evidence)")
    a = ap.parse_args()
    {"build": build, "run": lambda: run(a.model, a.limit, a.rerun), "summary": summary, "compare": compare}[a.cmd]()
