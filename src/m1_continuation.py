"""M1: verbatim continuation (GEMA / NYT Exhibit J style) through the API.

Neutral prompt: give the headline + first PREFIX words of the body and ask the model to continue the text.
Score the continuation against the true next words: longest common word run (LCS-substring) and
share of the model's 8-grams found in the original. Members vs controls.

Usage:
  python -I src/m1_continuation.py --model claude-sonnet-4-5-20250929 --n 60
"""
import argparse, concurrent.futures as cf, json, os, re, sys
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))
from probe import ask  # noqa: E402
from m2_decop import load, CONTROL_MIN_DATE  # noqa: E402,F401

PREFIX = 60
EXP = "m1_continuation"
PROMPT = """Continúa el siguiente texto (unas 150 palabras), sin comentarios previos:

{title}

{prefix}"""


def toks(s):
    return re.findall(r"\w+", s.lower())


def score(gen, true):
    a, b = toks(gen), toks(true)
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    g = lambda x, n: set(zip(*[x[i:] for i in range(n)]))
    ga = g(a, 8)
    return {"lcs_words": m.size, "lcs_text": " ".join(a[m.a:m.a + m.size]),
            "ngram8_overlap": (len(ga & g(b, 8)) / len(ga)) if ga else 0.0, "gen_words": len(a)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--inputs", nargs="+", default=["data/cc/members.jsonl", "data/cc/controls.jsonl"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    # same article sample as DE-COP when available
    ids = None
    pp = f"data/decop/paraphrases_minimal_{a.tag}.jsonl" if a.tag else "data/decop/paraphrases.jsonl"
    if os.path.exists(pp):
        ids = {json.loads(l)["id"] for l in open(pp)}
    docs = [d for d in load(a.inputs) if ids is None or d["id"] in ids]
    by = defaultdict(list)
    for d in docs:
        by[d["set"]].append(d)
    docs = by["member"][: a.n] + by["control"][: a.n]
    out = f"results/m1_continuation_{a.tag + '_' if a.tag else ''}{a.model}.jsonl"
    done = {json.loads(l)["id"] for l in open(out)} if os.path.exists(out) else set()

    def work(d):
        w = d["text"].split()
        prefix, true = " ".join(w[:PREFIX]), " ".join(w[PREFIX:PREFIX + 200])
        txt, rec = ask(EXP, a.model, PROMPT.format(title=d["title"], prefix=prefix), max_tokens=400,
                       meta={"id": d["id"], "set": d["set"]})
        if rec["stop_reason"] == "api_error":
            return None
        return {"id": d["id"], "set": d["set"], "pub_date": d["pub_date"], "model": a.model,
                "request_id": rec["request_id"], "stop_reason": rec["stop_reason"], **score(txt, true)}

    with open(out, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(work, [d for d in docs if d["id"] not in done]):
            if r is None:
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
    rows = [json.loads(l) for l in open(out)]
    for s in ("member", "control"):
        rs = [r for r in rows if r["set"] == s]
        if rs:
            lcs = sorted(r["lcs_words"] for r in rs)
            print(f"{s:8s} n={len(rs)} median LCS={lcs[len(lcs)//2]} max LCS={lcs[-1]} "
                  f">=10 words: {sum(x >= 10 for x in lcs)}  mean 8-gram overlap={sum(r['ngram8_overlap'] for r in rs)/len(rs):.1%}")
    top = sorted(rows, key=lambda r: -r["lcs_words"])[:5]
    for r in top:
        print(f"  {r['set']} {r['id']} LCS={r['lcs_words']}: {r['lcs_text'][:150]}")


if __name__ == "__main__":
    main()
