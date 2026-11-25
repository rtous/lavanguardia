"""M9: sentence-level "decomposition" extraction (adapted from Su et al. 2024, arXiv:2409.12367).

Su et al. recovered verbatim sentences from 73 of 3,723 NYT articles (0 of 900 post-cutoff controls) by asking a
frontier model, one sentence at a time, for "the sentence that immediately follows" a given sentence of a named
article. Unlike whole-article continuation (M1), each query is short, and the model is anchored on the title,
author and date. We keep their plain prompt and drop the role-play / jailbreak system prompts on purpose: a court must
not see "manipulated prompts" (the NYT-case objection, paper Section on the NYT dispute).

Per article: the first K body sentences of at least 8 words; for i = 1..K ask for sentence i given sentence i-1.
Scores per sentence: exact match after normalisation, fuzzy ratio (difflib) and longest common word run. A hit
INSIDE quotation marks in the original is flagged separately, because quotes (statements, rulings) are syndicated
across outlets and are not the newspaper's wording. Members vs controls (post-cutoff) give the base rate.

Usage: python -I src/m9_decomposition.py --model gemini-3.1-flash-lite --n 60 --k 4 [--tag lacontra]
"""
import argparse, concurrent.futures as cf, json, os, re, sys, unicodedata
from collections import defaultdict
from difflib import SequenceMatcher

sys.path.insert(0, os.path.dirname(__file__))
from probe import ask  # noqa: E402
from m2_decop import load  # noqa: E402

EXP = "m9_decomposition"
PROMPT = """Estoy buscando un artículo de La Vanguardia: «{title}»{by}, publicado el {date}.
Una de sus frases es: «{prev}»
¿Cuál es la frase que viene inmediatamente después en ese artículo? Escríbela entre triples comillas (```), solo esa frase."""


def sentences(text, min_words=8):
    paras = [p for p in text.split("\n") if len(p.split()) >= 25] or [text]
    out = []
    for p in paras:
        for s in re.split(r"(?<=[\.\?!»”])\s+(?=[«“\"¿¡A-ZÁÉÍÓÚÑ])", p):
            s = s.strip()
            if out and re.search(r"(^|\s)\w{1,2}\.$", out[-1]):   # abbreviation such as "v." or "Sr.": merge back
                out[-1] += " " + s
            elif s:
                out.append(s)
    return [s for s in out if len(s.split()) >= min_words]


def norm(s):
    s = unicodedata.normalize("NFKC", s).lower()
    return " ".join(re.findall(r"\w+", s))


def in_quotes(sent, text=None):
    """Conservative: any quotation mark in the sentence flags it, since quoted statements are syndicated across
    outlets and are not the newspaper's own wording. (Pairing quote marks over the whole text is unreliable.)"""
    return bool(re.search(r"[«»“”\"]", sent))


def score(gen, true):
    g = re.findall(r"```(.*?)```", gen, flags=re.S)
    g = (g[0] if g else gen).strip()
    a, b = norm(g).split(), norm(true).split()
    m = SequenceMatcher(None, a, b, autojunk=False).find_longest_match(0, len(a), 0, len(b))
    return {"gen": g, "exact": norm(g) == norm(true), "ratio": round(SequenceMatcher(None, a, b, autojunk=False).ratio(), 3),
            "lcs_words": m.size, "true_words": len(b)}


def one(d, i, sents, model):
    prev, true = sents[i - 1], sents[i]
    by = f" de {d['author']}" if d.get("author") else ""
    date = f"{d['pub_date'][6:8]}/{d['pub_date'][4:6]}/{d['pub_date'][:4]}"
    title = d["title"].split(" por ")[0] if d.get("author") else d["title"]
    text, rec = ask(EXP, model, PROMPT.format(title=title, by=by, date=date, prev=prev), max_tokens=300,
                    meta={"id": d["id"], "set": d["set"], "i": i})
    if rec["stop_reason"] == "api_error":
        return None, str(rec["response"])[:200]
    return {"id": d["id"], "set": d["set"], "i": i, "model": model, "sha256": rec["sha256"], "true": true,
            "true_in_quotes": in_quotes(true, d["text"]), **score(text, true)}, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=60, help="articles per set")
    ap.add_argument("--k", type=int, default=4, help="sentences asked per article")
    ap.add_argument("--inputs", nargs="+", default=["data/cc/members.jsonl", "data/cc/controls.jsonl"])
    ap.add_argument("--workers", type=int, default=2)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    by = defaultdict(list)
    for d in load(a.inputs):
        if "directo" not in d["url"] and len(sentences(d["text"])) > a.k:
            by[d["set"]].append(d)
    docs = by["member"][: a.n] + by["control"][: a.n]
    out = f"results/m9_decomposition_{a.tag + '_' if a.tag else ''}{a.model}.jsonl"
    done = {(r["id"], r["i"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    jobs = [(d, i, sentences(d["text"])) for d in docs for i in range(1, a.k + 1) if (d["id"], i) not in done]
    print(len(jobs), "queries to run", flush=True)
    with open(out, "a") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for row, err in ex.map(lambda j: one(*j, a.model), jobs):
            if err:
                print("api_error", err, flush=True)
                if "per day" in err.lower() or "credit balance" in err:
                    os._exit(1)
                continue
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            if row["exact"] or row["lcs_words"] >= 8:
                print("HIT", row["set"], row["id"], row["i"], row["lcs_words"], "quote" if row["true_in_quotes"] else "", row["gen"][:120], flush=True)
    rows = [json.loads(l) for l in open(out)]
    for s in ("member", "control"):
        rs = [r for r in rows if r["set"] == s]
        if rs:
            own = [r for r in rs if not r["true_in_quotes"]]
            print(f"{s}: n={len(rs)} exact={sum(r['exact'] for r in rs)} lcs>=8={sum(r['lcs_words'] >= 8 for r in rs)} "
                  f"| outside quotes: exact={sum(r['exact'] for r in own)} lcs>=8={sum(r['lcs_words'] >= 8 for r in own)} "
                  f"articles_with_hit={len({r['id'] for r in own if r['lcs_words'] >= 8})}")


if __name__ == "__main__":
    main()
