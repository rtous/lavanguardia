"""M13b: dense probe of the Garnier interview (pre-registered: docs/prereg/m13b_garnier_dense.md).

Prompts every 50 words (M13's prompts), 3 attempts per window, score = longest run shared with the article OUTSIDE the
prompt window (whole article minus the prefix), so matches with other parts of the article count. Controls: the first 4
La Contra controls of M13's offset-control list.
  python -I src/m13b_garnier.py run --model claude-opus-4-5-20251101
  python -I src/m13b_garnier.py run --model gemini-3.1-flash-lite
  python -I src/m13b_garnier.py summary            -> results/m13b_garnier_summary.json
"""
import argparse, json, os, sys
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m11_nyt_style import PREFIX, MAX_TOKENS, TEMPERATURE, TOP_P, norm_tokens, quoted  # noqa: E402
from m13_most_copied import members, offset_controls, prompt  # noqa: E402

EXP = "m13b_garnier"
GARNIER, STEP, MIN_AFTER, N_ATT, N_CONTROLS = "54068170076", 50, 50, 3, 4
LONG, ECHO, ADJ = 12, 6, 250


def items():
    g = [d for d in members() if d["id"] == GARNIER]
    c = [dict(d, set="control") for d in offset_controls() if d["tag"] == "lacontra"][:N_CONTROLS]
    return [dict(g[0], set="garnier")] + c


def windows(n):
    return list(range(0, n - PREFIX - MIN_AFTER + 1, STEP))


def score(gen, words, a, b):
    """Longest run between gen and the article outside words[a:b]; returns run, start TOKEN index in article, quote flag."""
    g = norm_tokens(gen)
    best = (0, None, "", False)
    for lo, hi in ((0, a), (b, len(words))):
        seg_words = words[lo:hi]
        seg = norm_tokens(" ".join(seg_words))
        m = SequenceMatcher(None, g, seg, autojunk=False).find_longest_match(0, len(g), 0, len(seg))
        if m.size > best[0]:
            run = seg[m.b:m.b + m.size]
            lo_tok = len(norm_tokens(" ".join(words[:lo])))  # token position of the segment start in the article
            best = (m.size, lo_tok + m.b, " ".join(run), quoted(run, " ".join(words)))
    return {"lcs_words": best[0], "match_start_token": best[1], "lcs_text": best[2], "lcs_in_quotes": best[3]}


def ask_n(model, msgs, system, seed, meta):
    from probe import ask, ask_gemini
    out, recs = [], []
    for i in range(N_ATT):
        m = dict(meta, attempt=i)
        if model.startswith("gemini"):
            kw = {} if i == 0 else dict(temperature=TEMPERATURE, top_p=TOP_P, seed=(seed + i) % (2 ** 31))
            t, r = ask_gemini(EXP, model, msgs, system=system, max_tokens=MAX_TOKENS, meta=m, **kw)
        else:
            t, r = ask(EXP, model, msgs, system=system, max_tokens=MAX_TOKENS, meta=m)
        if r["stop_reason"] == "api_error" and any(k in json.dumps(r["response"]) for k in ("per day", "limit: 0", "credit", "billing")):
            sys.exit(f"quota/billing error, stopping: {json.dumps(r['response'])[:300]}")
        out.append(t); recs.append(r)
    return out, recs


def run(model):
    out = f"results/m13b_garnier_{model}.jsonl"
    done = {(r["id"], r["offset"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [(d, a) for d in items() for a in windows(len(d["text"].split())) if (d["id"], a) not in done]
    print(f"{model}: {len(todo)} windows to run", flush=True)
    with open(out, "a", encoding="utf-8") as f:
        for k, (d, a) in enumerate(todo):
            words = d["text"].split(); b = a + PREFIX
            system, msgs = prompt(d, a, b, mid=a > 0)
            texts, recs = ask_n(model, msgs, system, int(d["id"]) + a, {"id": d["id"], "set": d["set"], "offset": a})
            att = [score(t, words, a, b) for t in texts]
            own = [x for x in att if not x["lcs_in_quotes"]] or [{"lcs_words": 0, "match_start_token": None, "lcs_text": ""}]
            bst = max(own, key=lambda x: x["lcs_words"])
            row = {"id": d["id"], "set": d["set"], "offset": a, "model": model,
                   "model_reported": sorted({str(r["model_reported"]) for r in recs}), "sha256": [r["sha256"] for r in recs],
                   "stop_reasons": [str(r["stop_reason"]) for r in recs], "best_outside_quotes": bst["lcs_words"],
                   "best_text": bst["lcs_text"], "best_match_start_token": bst["match_start_token"], "attempts": att}
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            print(f"{k + 1}/{len(todo)} {d['set']} {d['id']} off={a} best={bst['lcs_words']} | {bst['lcs_text'][:80]}", flush=True)


def summary():
    from scipy.stats import fisher_exact, mannwhitneyu
    res = {}
    for f in sorted(os.listdir("results")):
        if not (f.startswith("m13b_garnier_") and f.endswith(".jsonl")):
            continue
        R = [json.loads(l) for l in open(f"results/{f}")]
        name = f[len("m13b_garnier_"):-6]
        tok_off = {}  # token index of each prefix end, to tell echoes from continuations
        for d in items():
            w = d["text"].split()
            tok_off[d["id"]] = {a: len(norm_tokens(" ".join(w[:a + PREFIX]))) for a in windows(len(w))}
        def echo(r):
            for x in r["attempts"]:
                if x["lcs_in_quotes"] or x["lcs_words"] < ECHO or x["match_start_token"] is None:
                    continue
                pe = tok_off[r["id"]][r["offset"]]
                if not (pe <= x["match_start_token"] < pe + ADJ):  # not a continuation of the prompt
                    return True
            return False
        g = [r for r in R if r["set"] == "garnier"]; c = [r for r in R if r["set"] == "control"]
        gx, cx = [r["best_outside_quotes"] for r in g], [r["best_outside_quotes"] for r in c]
        ge, ce = sum(map(echo, g)), sum(map(echo, c))
        res[name] = {
            "n_windows": {"garnier": len(g), "control": len(c)},
            "primary_mw_one_sided_p": float(mannwhitneyu(gx, cx, alternative="greater").pvalue) if gx and cx else None,
            "median": {"garnier": sorted(gx)[len(gx) // 2] if gx else None, "control": sorted(cx)[len(cx) // 2] if cx else None},
            "max": {"garnier": max(gx, default=None), "control": max(cx, default=None)},
            f"windows_ge_{LONG}": {"garnier": sum(x >= LONG for x in gx), "control": sum(x >= LONG for x in cx)},
            "echo_windows": {"garnier": ge, "control": ce,
                             "fisher_one_sided_p": float(fisher_exact([[ge, len(g) - ge], [ce, len(c) - ce]], alternative="greater")[1]) if g and c else None},
            "garnier_runs": sorted(((r["best_outside_quotes"], r["offset"], r["best_text"]) for r in g), reverse=True)[:8],
        }
    json.dump(res, open("results/m13b_garnier_summary.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "summary"]); ap.add_argument("--model")
    a = ap.parse_args()
    {"run": lambda: run(a.model), "summary": summary}[a.cmd]()
