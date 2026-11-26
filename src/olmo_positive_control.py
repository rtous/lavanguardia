"""Positive control: do our tests detect La Vanguardia text in a model KNOWN to have been trained on it?

OLMo 2 (AI2) publishes its pretraining data (OLMo-mix-1124), and the public infini-gram service counts exact
occurrences of any token sequence in it (index v4_olmo-mix-1124_llama). So, unlike for commercial models, we can
verify which of our articles were in the training data, and how many times.

Stages (each resumable, outputs under results/olmo/):
  lookup     For each article, three 12-word spans from start/middle/end of the body (sentences with quotation marks
             skipped: quotes are syndicated). Count each span in OLMo-mix-1124. in_data = any span found.
             -> results/olmo/lookup.jsonl   (sends public article text snippets to api.infini-gram.io)
  split      Writes in-data / not-in-data article files for the same publication period (2020-2023), the cleanest
             possible member/control split (no time gap): data/olmo/{in,out}_{random,lacontra}.jsonl
  continue   Verbatim continuation on OLMo (local MLX, greedy, raw page completion): 60-word prefix, 80 new tokens;
             longest common word run with the true next 200 words. -> results/olmo/continuation.jsonl
Word-probability scores use src/m5_logprob.py on the split files; La Contra Q->A uses src/m10_exclusive_facts.py
(analysis joins by URL). Summary: `summary` -> results/olmo/summary.json

Usage: python -I src/olmo_positive_control.py lookup|split|continue|summary [--model ...]
"""
import argparse, concurrent.futures as cf, glob, json, os, random, re, sys, time
from difflib import SequenceMatcher

import requests

sys.path.insert(0, os.path.dirname(__file__))
API, INDEX = "https://api.infini-gram.io/", "v4_olmo-mix-1124_llama"
OUT = "results/olmo"
MODEL = "mlx-community/OLMo-2-1124-7B-Instruct-4bit"
SOURCES = {"members": "random", "mid2023": "random", "lacontra_members": "lacontra",
           "controls": "random_ctrl", "lacontra_controls_more": "lacontra_ctrl"}


def spans(text, n=3, w=12):
    sents = [s.strip() for s in re.split(r"(?<=[\.\?!])\s+", text.replace("\n", " "))]
    ok = [s for s in sents if len(s.split()) >= w + 2 and not re.search(r"[«»“”\"]", s) and "- " not in s]
    if not ok:
        return []
    idx = sorted({0, len(ok) // 2, len(ok) - 1})[:n]
    return [" ".join(ok[i].split()[:w]) for i in idx]


def count(q, tries=6):
    for k in range(tries):
        try:
            r = requests.post(API, json={"index": INDEX, "query_type": "count", "query": q}, timeout=60).json()
            if "error" not in r:
                return r["count"]
        except Exception:
            pass
        time.sleep(2 * (k + 1))
    return None


def lookup():
    os.makedirs(OUT, exist_ok=True)
    path = f"{OUT}/lookup.jsonl"
    done = {json.loads(l)["url"] for l in open(path)} if os.path.exists(path) else set()
    todo = []
    for f, group in SOURCES.items():
        arts = [json.loads(l) for l in open(f"data/cc/{f}.jsonl")]
        if group.endswith("ctrl"):
            arts = random.Random(0).sample(arts, min(60, len(arts)))  # sanity check: should all be absent
        todo += [(group, a) for a in arts if a["url"] not in done]
    print("articles to look up:", len(todo), flush=True)

    def one(ga):
        g, a = ga
        sp = spans(a["text"])
        cs = [count(s) for s in sp]
        time.sleep(0.2)
        return {"url": a["url"], "group": g, "pub_date": a["pub_date"], "section": a["section"], "spans": sp,
                "counts": cs, "in_data": any((c or 0) > 0 for c in cs), "max_count": max([c or 0 for c in cs] or [0]),
                "lookup_ok": bool(sp) and all(c is not None for c in cs), "index": INDEX}

    with open(path, "a") as fo, cf.ThreadPoolExecutor(3) as ex:
        for i, r in enumerate(ex.map(one, todo)):
            fo.write(json.dumps(r, ensure_ascii=False) + "\n")
            fo.flush()
            if i % 100 == 99:
                print(f"  {i + 1}/{len(todo)}", flush=True)


def split():
    rows = [json.loads(l) for l in open(f"{OUT}/lookup.jsonl")]
    arts = {}
    for f in SOURCES:
        for l in open(f"data/cc/{f}.jsonl"):
            a = json.loads(l)
            arts[a["url"]] = a
    os.makedirs("data/olmo", exist_ok=True)
    stats = {}
    for g in ("random", "lacontra"):
        for flag, name in ((True, "in"), (False, "out")):
            sel = [arts[r["url"]] for r in rows if r["group"] == g and r["lookup_ok"] and r["in_data"] == flag
                   and r["pub_date"] <= "20231231"]
            with open(f"data/olmo/{name}_{g}.jsonl", "w") as fo:
                for a in sel:
                    fo.write(json.dumps(a, ensure_ascii=False) + "\n")
            stats[f"{name}_{g}"] = len(sel)
    print(stats)


def lcs(a, b):
    a, b = a.lower().split(), b.lower().split()
    return SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b)).size


def cont(model, n):
    from probe import ask
    path = f"{OUT}/continuation.jsonl"
    done = {json.loads(l)["url"] for l in open(path)} if os.path.exists(path) else set()
    with open(path, "a") as fo:
        for name in ("in_random", "out_random", "in_lacontra", "out_lacontra"):
            arts = [json.loads(l) for l in open(f"data/olmo/{name}.jsonl")]
            random.Random(0).shuffle(arts)
            for a in arts[:n]:
                if a["url"] in done:
                    continue
                w = a["text"].split()
                if len(w) < 300:
                    continue
                prefix, true = " ".join(w[:60]), " ".join(w[60:260])
                prompt = f"La Vanguardia\n{a['title']}\n\n{prefix}"
                gen, rec = ask("olmo_positive_control", model, prompt, max_tokens=80, raw=True,
                               meta={"url": a["url"], "group": name})
                fo.write(json.dumps({"url": a["url"], "group": name, "gen": gen, "lcs_words": lcs(gen, true),
                                     "evidence_sha256": rec["sha256"], "model_reported": rec["model_reported"]},
                                    ensure_ascii=False) + "\n")
                fo.flush()
            print(f"  {name} done", flush=True)


def summary():
    import statistics as st
    from scipy.stats import mannwhitneyu
    rows = [json.loads(l) for l in open(f"{OUT}/lookup.jsonl")]
    res = {"lookup": {}}
    for g in sorted({r["group"] for r in rows}):
        rs = [r for r in rows if r["group"] == g and r["lookup_ok"]]
        found = [r for r in rs if r["in_data"]]
        res["lookup"][g] = {"n": len(rs), "in_data": len(found),
                            "max_count_median_if_found": st.median([r["max_count"] for r in found]) if found else None,
                            "repeated_10plus": sum(r["max_count"] >= 10 for r in found)}
    if os.path.exists(f"{OUT}/continuation.jsonl"):
        c = [json.loads(l) for l in open(f"{OUT}/continuation.jsonl")]
        res["continuation"] = {}
        for g in ("random", "lacontra"):
            a = [r["lcs_words"] for r in c if r["group"] == f"in_{g}"]
            b = [r["lcs_words"] for r in c if r["group"] == f"out_{g}"]
            if a and b:
                res["continuation"][g] = {"in_n": len(a), "out_n": len(b), "in_median": st.median(a), "in_max": max(a),
                                          "out_median": st.median(b), "out_max": max(b),
                                          "p_in_gt_out": round(mannwhitneyu(a, b, alternative="greater").pvalue, 4)}
    for f, key in (("m5_olmo2_random.jsonl", "logprob_random"), ("m5_olmo2_lacontra.jsonl", "logprob_lacontra")):
        p = f"results/olmo/{f}"
        if os.path.exists(p):
            from sklearn.metrics import roc_auc_score
            s = [json.loads(l) for l in open(p)]
            y = [1 if r["set"] == "in" else 0 for r in s]
            res[key] = {"n_in": sum(y), "n_out": len(y) - sum(y)}
            for m, sign in (("loss", -1), ("zlib", -1), ("mink", 1), ("minkpp", 1)):
                if m in s[0]:
                    sc = [sign * r[m] for r in s]
                    res[key][f"auc_{m}"] = round(roc_auc_score(y, sc), 3)
                    res[key][f"p_{m}"] = round(mannwhitneyu([x for x, t in zip(sc, y) if t], [x for x, t in zip(sc, y) if not t],
                                                            alternative="greater").pvalue, 4)
    json.dump(res, open(f"{OUT}/summary.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["lookup", "split", "continue", "summary"])
    ap.add_argument("--model", default=MODEL)
    ap.add_argument("--n", type=int, default=100)
    a = ap.parse_args()
    {"lookup": lookup, "split": split, "continue": lambda: cont(a.model, a.n), "summary": summary}[a.cmd]()
