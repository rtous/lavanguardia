"""M2: DE-COP (Duarte et al., ICML 2024) multiple-choice verbatim-recognition test.

For each article: take a ~70-word passage from the start of the body, generate 3 paraphrases (cached),
then ask the target model 4 times (verbatim passage rotated through A-D) which option is the exact text
published in La Vanguardia. Chance = 25%. Compare accuracy on members (published before the model's
training cutoff and present in Common Crawl) vs controls (published after the cutoff).

Usage:
  python -I src/m2_decop.py paraphrase --inputs data/cc/members.jsonl data/cc/controls.jsonl --n 60
  python -I src/m2_decop.py test --model claude-sonnet-4-5-20250929 --n 60
  python -I src/m2_decop.py report
"""
import argparse, concurrent.futures as cf, json, os, random, re, sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from probe import ask  # noqa: E402

PARA_MODEL = "claude-opus-5-5"
PARA_PATH = PARA_PATH_FULL = "data/decop/paraphrases.jsonl"  # style=full
PARA_PATH_MIN = "data/decop/paraphrases_minimal.jsonl"  # style=minimal
EXP = "m2_decop"
LETTERS = "ABCD"
CONTROL_MIN_DATE = "20250901"   # after training-data cutoff of Claude Sonnet/Haiku 4.5 (Jul 2025), Opus 4.5 (Aug 2025)


def passage(text, target=70):
    words = text.split()
    # skip a leading line that is just the headline/subhead (short first paragraph)
    paras = [p for p in text.split("\n") if len(p.split()) >= 25]
    body = " ".join(paras) if paras else text
    words = body.split()
    cut = target
    # extend to the end of the sentence (max +30 words)
    for j in range(target, min(len(words), target + 30)):
        if re.search(r"[\.\?!»”\"]$", words[j - 1]):
            cut = j
            break
    return " ".join(words[:cut])


def load(paths):
    out = []
    for p in paths:
        label = "member" if "member" in os.path.basename(p) else "control"
        for l in open(p, encoding="utf-8"):
            d = json.loads(l)
            if label == "control" and d["pub_date"] < CONTROL_MIN_DATE:
                continue
            d["set"] = label
            out.append(d)
    return out


PARA_PROMPT = """Reescribe el siguiente fragmento periodístico en español de tres maneras distintas.
Cada versión debe conservar exactamente el mismo significado, los mismos datos y nombres propios y una longitud similar,
pero con redacción claramente diferente (otro orden, otras palabras). No añadas ni quites información.
Devuelve solo un objeto JSON: {{"p1": "...", "p2": "...", "p3": "..."}}

Fragmento:
{passage}"""


PARA_PROMPT_MIN = """A continuación tienes un fragmento periodístico en español. Crea tres variantes casi idénticas:
en cada una sustituye solo entre 6 y 8 palabras o expresiones por sinónimos o equivalentes naturales
(distintas sustituciones en cada variante), dejando todo lo demás exactamente igual: mismo orden, misma puntuación,
mismos datos y nombres propios. Las variantes deben sonar igual de naturales que el original.
Devuelve solo un objeto JSON: {{"p1": "...", "p2": "...", "p3": "..."}}

Fragmento:
{passage}"""


def cmd_paraphrase(a):
    global PARA_PATH, PARA_PROMPT, PARA_PATH_FULL
    if a.style == "minimal":
        PARA_PATH, PARA_PROMPT = PARA_PATH_MIN, PARA_PROMPT_MIN
    if a.tag:
        PARA_PATH = PARA_PATH.replace(".jsonl", f"_{a.tag}.jsonl")
        PARA_PATH_FULL = PARA_PATH_FULL.replace(".jsonl", f"_{a.tag}.jsonl")
    os.makedirs(os.path.dirname(PARA_PATH), exist_ok=True)
    done = {json.loads(l)["id"] for l in open(PARA_PATH)} if os.path.exists(PARA_PATH) else set()
    docs = load(a.inputs)
    rng = random.Random(0)
    by = defaultdict(list)
    for d in docs:
        by[d["set"]].append(d)
    todo = []
    if a.style == "minimal" and os.path.exists(PARA_PATH_FULL):
        keep = {json.loads(l)["id"] for l in open(PARA_PATH_FULL)}
        by = {k: [d for d in v if d["id"] in keep] for k, v in by.items()}
    for s, ds in by.items():
        rng.shuffle(ds)
        todo += [d for d in ds[: a.n] if d["id"] not in done]

    def work(d):
        p = passage(d["text"])
        txt, _ = ask("paraphrases", PARA_MODEL, PARA_PROMPT.format(passage=p), max_tokens=3000,
                     meta={"id": d["id"]})
        m = re.search(r"\{.*\}", txt, re.S)
        if not m:
            return None
        try:
            j = json.loads(m.group(0))
            return {"id": d["id"], "set": d["set"], "pub_date": d["pub_date"], "title": d["title"],
                    "passage": p, "paraphrases": [j["p1"], j["p2"], j["p3"]], "para_model": PARA_MODEL,
                    "style": a.style}
        except Exception:
            return None

    with open(PARA_PATH, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(4) as ex:
        for r in ex.map(work, todo):
            if r:
                f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()
    print("paraphrases:", sum(1 for _ in open(PARA_PATH)))


Q = """Pregunta: ¿Cuál de los siguientes fragmentos es el texto literal (palabra por palabra) del artículo "{title}" publicado en La Vanguardia?
Solo uno es el original; los otros son paráfrasis.

A. {A}

B. {B}

C. {C}

D. {D}

Responde únicamente con la letra (A, B, C o D)."""

Q_V2 = Q.replace("Responde únicamente con la letra (A, B, C o D).",
                 "Es una prueba de opción múltiple: debes elegir siempre una opción, aunque no estés seguro. "
                 "Responde únicamente con la letra (A, B, C o D), sin explicación.")


def cmd_test(a):
    src = PARA_PATH_MIN if a.style == "minimal" else PARA_PATH
    items = [json.loads(l) for l in open(src, encoding="utf-8")]
    by = defaultdict(list)
    for it in items:
        by[it["set"]].append(it)
    items = by["member"][: a.n] + by["control"][: a.n]
    out_path = f"results/m2_decop_{a.style}_v2_{a.model}.jsonl"
    os.makedirs("results", exist_ok=True)
    done = {(json.loads(l)["id"], json.loads(l)["rot"]) for l in open(out_path)} if os.path.exists(out_path) else set()
    jobs = [(it, r) for it in items for r in range(4) if (it["id"], r) not in done]

    def work(job):
        it, r = job
        opts = list(it["paraphrases"])
        opts.insert(r, it["passage"])          # verbatim at position r
        prompt = Q_V2.format(title=it["title"], **dict(zip(LETTERS, opts)))
        txt, rec = ask(EXP, a.model, prompt, max_tokens=60,
                       meta={"id": it["id"], "set": it["set"], "rot": r, "style": a.style, "prompt": "v2"})
        t = txt.strip()
        m = re.match(r"^\**([ABCD])\b", t) or re.search(r"(?:respuesta|opci[oó]n)\W+(?:es\W+)?\**([ABCD])\b", t, re.I)
        ans = m.group(1) if m else None
        if rec["stop_reason"] == "api_error":
            return None
        return {"id": it["id"], "set": it["set"], "pub_date": it["pub_date"], "rot": r, "model": a.model,
                "style": a.style, "prompt": "v2",
                "answer": ans, "raw": txt[:50], "correct": ans == LETTERS[r], "request_id": rec["request_id"]}

    with open(out_path, "a", encoding="utf-8") as f, cf.ThreadPoolExecutor(a.workers) as ex:
        for i, res in enumerate(ex.map(work, jobs)):
            if res is None:
                continue
            f.write(json.dumps(res, ensure_ascii=False) + "\n"); f.flush()
            if i % 50 == 0:
                print(i, len(jobs), res, flush=True)
    cmd_report(a)


def cmd_report(a):
    from scipy.stats import binomtest, mannwhitneyu
    import glob
    for path in sorted(glob.glob("results/m2_decop_*.jsonl")):
        rows = [json.loads(l) for l in open(path)]
        print(f"\n== {path}")
        per = defaultdict(list)
        for r in rows:
            per[(r["set"], r["id"])].append(r["correct"])
        for s in ("member", "control"):
            rs = [r for r in rows if r["set"] == s]
            if not rs:
                continue
            k = sum(r["correct"] for r in rs); n = len(rs)
            none = sum(r["answer"] is None for r in rs)
            p = binomtest(k, n, 0.25, alternative="greater").pvalue
            pos = defaultdict(int)
            for r in rs:
                pos[r["answer"]] += 1
            print(f"  {s:8s} acc={k/n:.1%} ({k}/{n}, {len({i for (ss,i) in per if ss==s})} articles)  "
                  f"p(>chance)={p:.1e}  unparsed={none}  answer dist={dict(pos)}")
        m = [sum(v) / len(v) for (s, _), v in per.items() if s == "member"]
        c = [sum(v) / len(v) for (s, _), v in per.items() if s == "control"]
        if len(m) > 4 and len(c) > 4:
            u = mannwhitneyu(m, c, alternative="greater")
            print(f"  member vs control (per-article acc): Mann-Whitney p={u.pvalue:.2e}")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("paraphrase"); p.add_argument("--inputs", nargs="+", required=True); p.add_argument("--n", type=int, default=60)
    p.add_argument("--style", choices=["full", "minimal"], default="full")
    p.add_argument("--tag", default="")
    t = sub.add_parser("test"); t.add_argument("--model", required=True); t.add_argument("--n", type=int, default=60); t.add_argument("--workers", type=int, default=6)
    t.add_argument("--style", choices=["full", "minimal"], default="full")
    sub.add_parser("report")
    a = ap.parse_args()
    {"paraphrase": cmd_paraphrase, "test": cmd_test, "report": cmd_report}[a.cmd](a)


if __name__ == "__main__":
    main()
