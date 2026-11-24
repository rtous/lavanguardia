"""M2b: pairwise (2-alternative forced choice) verbatim recognition.

Fixes a flaw of 4-option DE-COP with minimal edits: when 3 variants each change different words, the
original is the "consensus" text and can be found by majority vote without any memory. Here each question
shows only the original and ONE minimal-edit variant (order balanced). Chance = 50%.
Membership signal = accuracy(members) - accuracy(controls).

Usage: python -I src/m2b_pairwise.py --model claude-opus-4-5-20251101 --n 60
"""
import argparse, concurrent.futures as cf, json, os, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from probe import ask  # noqa: E402

SRC = "data/decop/paraphrases_minimal.jsonl"
EXP = "m2b_pairwise"
Q = """Pregunta: ¿Cuál de estos dos fragmentos es el texto literal (palabra por palabra) del artículo "{title}" publicado en La Vanguardia?
Uno es el original y el otro una versión con algunas palabras cambiadas.

A. {A}

B. {B}

Es una prueba de elección forzosa: elige siempre una opción, aunque no estés seguro. Responde únicamente con la letra (A o B)."""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", required=True)
    ap.add_argument("--n", type=int, default=60)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--tag", default="")
    a = ap.parse_args()
    src = SRC.replace(".jsonl", f"_{a.tag}.jsonl") if a.tag else SRC
    items = [json.loads(l) for l in open(src, encoding="utf-8")]
    by = defaultdict(list)
    for it in items:
        by[it["set"]].append(it)
    items = by["member"][: a.n] + by["control"][: a.n]
    out = f"results/m2b_pairwise_{a.tag + '_' if a.tag else ''}{a.model}.jsonl"
    done = {(json.loads(l)["id"], json.loads(l)["k"], json.loads(l)["orig_pos"]) for l in open(out)} if os.path.exists(out) else set()
    jobs = [(it, k, pos) for it in items for k in range(3) for pos in "AB" if (it["id"], k, pos) not in done]

    def work(job):
        it, k, pos = job
        opts = {"A": it["passage"], "B": it["paraphrases"][k]} if pos == "A" else {"A": it["paraphrases"][k], "B": it["passage"]}
        txt, rec = ask(EXP, a.model, Q.format(title=it["title"], **opts), max_tokens=60,
                       meta={"id": it["id"], "set": it["set"], "k": k, "orig_pos": pos})
        t = txt.strip()
        m = re.match(r"^\**([AB])\b", t) or re.search(r"(?:respuesta|opci[oó]n)\W+(?:es\W+)?\**([AB])\b", t, re.I)
        ans = m.group(1) if m else None
        if rec["stop_reason"] == "api_error":
            return None
        return {"id": it["id"], "set": it["set"], "pub_date": it["pub_date"], "k": k, "orig_pos": pos,
                "model": a.model, "answer": ans, "raw": t[:40], "correct": ans == pos, "request_id": rec["request_id"]}

    with open(out, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for r in ex.map(work, jobs):
            if r is None:
                continue
            f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
    report(out)


def report(path):
    from scipy.stats import binomtest, mannwhitneyu
    rows = [json.loads(l) for l in open(path)]
    print(f"== {path}")
    per = defaultdict(list)
    for r in rows:
        per[(r["set"], r["id"])].append(r["correct"])
    for s in ("member", "control"):
        rs = [r for r in rows if r["set"] == s]
        k, n = sum(r["correct"] for r in rs), len(rs)
        print(f"  {s:8s} acc={k/n:.1%} ({k}/{n})  p(>50%)={binomtest(k, n, 0.5, alternative='greater').pvalue:.1e}  "
              f"unparsed={sum(r['answer'] is None for r in rs)}  "
              f"A-bias={sum(r['answer']=='A' for r in rs)/n:.0%}")
    m = [sum(v) / len(v) for (s, _), v in per.items() if s == "member"]
    c = [sum(v) / len(v) for (s, _), v in per.items() if s == "control"]
    print(f"  member vs control per-article: Mann-Whitney p={mannwhitneyu(m, c, alternative='greater').pvalue:.2e}")


if __name__ == "__main__":
    main()
