"""M13c: M13b's dense probe on the next most-copied La Contra interviews (pre-registered: docs/prereg/m13c_lacontra_dense.md).
Members: #2 Gérvas, #3 wi-fi, #18 L'Ecuyer. Controls: M13b's 4 (rows reused) + 4 new La Contra controls.
  python -I src/m13c_lacontra.py run --model claude-opus-4-5-20251101
  python -I src/m13c_lacontra.py summary          -> results/m13c_lacontra_summary.json
"""
import argparse, json, os, statistics as st, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import m13b_garnier as B  # noqa: E402
from m11_nyt_style import PREFIX  # noqa: E402
from m13_most_copied import members, offset_controls, prompt  # noqa: E402

B.EXP = "m13c_lacontra"  # evidence/m13c_lacontra/calls.jsonl (ask_n logs under B.EXP)
MEMBERS = ("54365145790", "54228364832", "54360763481")
NEW_CONTROLS = ("11461087", "11480309", "11461945", "11462840")
M13B_CONTROLS = ("11458911", "11460053", "11478598", "11479519")


def new_items():
    m = [dict(d, set="member") for d in members() if d["id"] in MEMBERS]
    c = [dict(d, set="control") for d in offset_controls() if d["tag"] == "lacontra" and d["id"] in NEW_CONTROLS]
    assert len(m) == 3 and len(c) == 4
    return m + c


def run(model):
    out = f"results/m13c_lacontra_{model}.jsonl"
    done = {(r["id"], r["offset"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [(d, a) for d in new_items() for a in B.windows(len(d["text"].split())) if (d["id"], a) not in done]
    print(f"{model}: {len(todo)} windows to run", flush=True)
    with open(out, "a", encoding="utf-8") as f:
        for k, (d, a) in enumerate(todo):
            words = d["text"].split(); b = a + PREFIX
            system, msgs = prompt(d, a, b, mid=a > 0)
            texts, recs = B.ask_n(model, msgs, system, int(d["id"]) + a, {"id": d["id"], "set": d["set"], "offset": a})
            att = [B.score(t, words, a, b) for t in texts]
            own = [x for x in att if not x["lcs_in_quotes"]] or [{"lcs_words": 0, "match_start_token": None, "lcs_text": ""}]
            bst = max(own, key=lambda x: x["lcs_words"])
            row = {"id": d["id"], "set": d["set"], "offset": a, "model": model,
                   "model_reported": sorted({str(r["model_reported"]) for r in recs}), "sha256": [r["sha256"] for r in recs],
                   "stop_reasons": [str(r["stop_reason"]) for r in recs], "best_outside_quotes": bst["lcs_words"],
                   "best_text": bst["lcs_text"], "best_match_start_token": bst["match_start_token"], "attempts": att}
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            print(f"{k + 1}/{len(todo)} {d['set']} {d['id']} off={a} best={bst['lcs_words']} | {bst['lcs_text'][:80]}", flush=True)


def summary():
    from scipy.stats import mannwhitneyu
    res = {}
    for model in ("claude-opus-4-5-20251101", "gemini-3.1-flash-lite"):
        p, pb = f"results/m13c_lacontra_{model}.jsonl", f"results/m13b_garnier_{model}.jsonl"
        if not os.path.exists(p):
            continue
        R = [json.loads(l) for l in open(p)]
        Rb = [json.loads(l) for l in open(pb)] if os.path.exists(pb) else []
        R += [r for r in Rb if r["id"] in M13B_CONTROLS]          # reused controls
        garnier = [r for r in Rb if r["set"] == "garnier"]
        def per_article(rows):
            by = {}
            for r in rows:
                by.setdefault(r["id"], []).append(r["best_outside_quotes"])
            return {k: st.median(v) for k, v in by.items()}
        mem = per_article([r for r in R if r["set"] == "member"]); con = per_article([r for r in R if r["set"] == "control"])
        mw = lambda x, y: float(mannwhitneyu(x, y, alternative="greater").pvalue) if x and y else None
        mwin = [r["best_outside_quotes"] for r in R if r["set"] == "member"]
        cwin = [r["best_outside_quotes"] for r in R if r["set"] == "control"]
        g = per_article(garnier)
        res[model] = {
            "n_articles": {"member": len(mem), "control": len(con)},
            "article_medians": {"member": mem, "control": con},
            "primary_article_level_p": mw(list(mem.values()), list(con.values())),
            "secondary_window_level_p": mw(mwin, cwin),
            "windows": {"member": len(mwin), "control": len(cwin)},
            "max": {"member": max(mwin, default=None), "control": max(cwin, default=None)},
            "windows_ge_12": {"member": sum(x >= 12 for x in mwin), "control": sum(x >= 12 for x in cwin)},
            "with_garnier_article_level_p (not confirmatory)": mw(list(mem.values()) + list(g.values()), list(con.values())),
            "member_runs": sorted(((r["best_outside_quotes"], r["id"], r["offset"], r["best_text"]) for r in R if r["set"] == "member"), reverse=True)[:8],
            "complete": len(mwin) >= 44 and len(con) == 8,
        }
    json.dump(res, open("results/m13c_lacontra_summary.json", "w"), indent=1, ensure_ascii=False)
    print(json.dumps(res, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); ap.add_argument("cmd", choices=["run", "summary"]); ap.add_argument("--model")
    a = ap.parse_args(); {"run": lambda: run(a.model), "summary": summary}[a.cmd]()
