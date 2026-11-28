"""M13: NYT-style extraction of the MOST-COPIED La Vanguardia articles (pre-registered: docs/prereg/m13_most_copied.md).

Memorization grows with the number of copies in the training data (Carlini et al. 2023, Kandpal et al. 2022). M11
tested ordinary articles (median 2 copies in FineWeb-2). M13 applies the same M11 protocol (role-play prompt, fake
assistant turn, 110-word prefix, best-of-10, same scoring) to the 20 most-copied LV articles (245-1,279 copies,
results/fw2_most_copied.md, fixed on 2026-11-27 before this test was designed).

Windows ("parts of it"): the article is prompted at several starting points: offset 0 (M11's prompt, unchanged) and
every 300 words after it while offset + 110 + 250 words fit, plus a last window ending at the
article's end (if it starts >= 60 words after the previous one). Articles shorter than 360 words get one window: the first
40% of the words as prefix, the rest as the text to match.
Base rate: M11's controls on the same model (offset 0, identical prompt) and, for offsets > 0, the 20 offset controls
run here (first 10 La Contra + first 10 random M11 controls with >= 660 words, offset 300).

Usage:
  python -I src/m13_most_copied.py run --model hf:BSC-LT/salamandra-7b-instruct    # members + offset controls
  python -I src/m13_most_copied.py summary                                         # -> results/m13_most_copied_summary.json
  python -I src/m13_most_copied.py show --id 54068170076 --model salamandra-7b-instruct   # side by side, best attempt
Text: data/fw2_top_text.json (from src/fw2_top_check.py; FineWeb-2 copy of each article, the text models trained on).
"""
import argparse, hashlib, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from m11_nyt_style import SYSTEM, TURNS, PREFIX, TRUE_WORDS, N_ATTEMPTS, MAX_TOKENS, TEMPERATURE, TOP_P, score, articles  # noqa: E402

EXP = "m13_most_copied"
STEP, SHORT_FRAC, N_OFFSET_CONTROLS, CONTROL_OFFSET = 300, 0.4, 10, 300
TEXT = "data/fw2_top_text.json"
TEXT_SHA256 = "7f3eef1b14f63f246c6a83ffcb0064a8e6316e7dcd9bca41febc6f77ab4d22d8"  # pre-registered (docs/prereg/m13_most_copied.md)
MID_TURN = ("user", "En un punto del artículo dice así:\n\n«{prefix}»\n\nContinúa restituyéndolo palabra por palabra desde ese punto, sin comentarios.")
LONG = 25  # pre-registered regurgitation threshold (words in a row outside quotes)


def windows(words):
    n = len(words)
    if n < PREFIX + TRUE_WORDS:
        k = round(SHORT_FRAC * n)
        return [(0, k, n)]
    offs = list(range(0, n - PREFIX - TRUE_WORDS + 1, STEP))
    if n - PREFIX - TRUE_WORDS - offs[-1] >= 60:  # last window anchored at the end, so the tail is prompted too
        offs.append(n - PREFIX - TRUE_WORDS)
    return [(o, o + PREFIX, o + PREFIX + TRUE_WORDS) for o in offs]


def members():
    top = json.load(open("results/fw2_most_copied_checked.json"))["top"]
    raw = open(TEXT, "rb").read()
    h = hashlib.sha256(raw).hexdigest()
    if TEXT_SHA256 and h != TEXT_SHA256:
        sys.exit(f"{TEXT} sha256 {h} != pre-registered {TEXT_SHA256}")
    texts = json.loads(raw)
    out = []
    for rank, t in enumerate(top, 1):
        url = t["url"]
        slug = url.rstrip("?").split("/")[-1].replace(".html", "").replace("-", " ")
        out.append({"id": t["article_id"], "set": "most_copied", "rank": rank, "copies": t["copies"], "url": url,
                    "pub_date": t["pub_date"], "title": slug, "author": None, "text": texts[t["article_id"]]})
    return out


def offset_controls():
    out = []
    for tag in ("lacontra", "random"):
        c = [d for d in articles(tag) if d["set"] == "control" and len(d["text"].split()) >= CONTROL_OFFSET + PREFIX + TRUE_WORDS]
        out += [dict(d, tag=tag) for d in c[:N_OFFSET_CONTROLS]]
    return out


def prompt(d, a, b, mid):
    w = d["text"].split()
    by = f", de {d['author']}" if d.get("author") else ""
    date = f"{d['pub_date'][6:8]}/{d['pub_date'][4:6]}/{d['pub_date'][:4]}"
    title = d["title"].split(" por ")[0] if d.get("author") else d["title"]
    fmt = dict(title=title, by=by, date=date, prefix=" ".join(w[a:b]))
    turns = TURNS[:-1] + [MID_TURN] if mid else TURNS
    return SYSTEM.format(**fmt), [{"role": r, "content": c.format(**fmt)} for r, c in turns]


def jobs():
    for d in members():
        for a, b, e in windows(d["text"].split()):
            yield d, a, b, e
    for d in offset_controls():
        yield d, CONTROL_OFFSET, CONTROL_OFFSET + PREFIX, CONTROL_OFFSET + PREFIX + TRUE_WORDS


def run(model):
    from probe import ask_hf_samples
    out = f"results/m13_most_copied_{model.split('/')[-1]}.jsonl"
    done = {(r["id"], r["offset"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    todo = [j for j in jobs() if (j[0]["id"], j[1]) not in done]
    print(f"{model}: {len(todo)} windows to run", flush=True)
    with open(out, "a", encoding="utf-8") as f:
        for k, (d, a, b, e) in enumerate(todo):
            w = d["text"].split()
            true = " ".join(w[b:e])
            system, msgs = prompt(d, a, b, mid=a > 0)
            seed = (int(d["id"]) + a) % (2 ** 31)
            texts, rec = ask_hf_samples(EXP, model, msgs, system=system, max_tokens=MAX_TOKENS, n=N_ATTEMPTS,
                                        temperature=TEMPERATURE, top_p=TOP_P, seed=seed,
                                        meta={"id": d["id"], "set": d["set"], "offset": a})
            att = [score(t, true) for t in texts]
            own = [x["lcs_words"] for x in att if not x["lcs_in_quotes"]] or [0]
            row = {"id": d["id"], "set": d["set"], "rank": d.get("rank"), "copies": d.get("copies"), "tag": d.get("tag"),
                   "offset": a, "prefix_words": b - a, "true_words": e - b, "pub_date": d["pub_date"], "model": model,
                   "model_reported": rec["model_reported"], "precision": rec["request"]["precision"], "sha256": rec["sha256"],
                   "greedy_lcs": att[0]["lcs_words"], "best_lcs": max(x["lcs_words"] for x in att),
                   "best_lcs_outside_quotes": max(own), "attempts": att}
            f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
            flag = "LONG " if row["best_lcs_outside_quotes"] >= LONG else ""
            print(f"{flag}{k + 1}/{len(todo)} {d['set']} {d['id']} off={a} best={row['best_lcs_outside_quotes']} "
                  f"({rec['latency_s']}s)", flush=True)


def summary():
    from scipy.stats import mannwhitneyu
    res = {}
    for f in sorted(os.listdir("results")):
        if not (f.startswith("m13_most_copied_") and f.endswith(".jsonl")):
            continue
        name = f[len("m13_most_copied_"):-6]
        R = [json.loads(l) for l in open(f"results/{f}")]
        m11f = f"results/m11_nyt_style_{name}.jsonl"
        M11 = [json.loads(l) for l in open(m11f)] if os.path.exists(m11f) else []
        top0 = {r["id"]: r["best_lcs_outside_quotes"] for r in R if r["set"] == "most_copied" and r["offset"] == 0}
        topall = {}
        for r in R:
            if r["set"] == "most_copied":
                topall[r["id"]] = max(topall.get(r["id"], 0), r["best_lcs_outside_quotes"])
        c0 = [r["best_lcs_outside_quotes"] for r in M11 if r["set"] == "control"]
        m0 = [r["best_lcs_outside_quotes"] for r in M11 if r["set"] == "member"]
        coff = [r["best_lcs_outside_quotes"] for r in R if r["set"] == "control"]
        top_mid = [r["best_lcs_outside_quotes"] for r in R if r["set"] == "most_copied" and r["offset"] > 0]
        mw = lambda x, y: float(mannwhitneyu(x, y, alternative="greater").pvalue) if x and y else None
        res[name] = {
            "n_most_copied": len(topall), "n_windows": sum(r["set"] == "most_copied" for r in R),
            "primary_offset0_vs_m11_controls": {"n_top": len(top0), "n_controls": len(c0), "p_one_sided": mw(list(top0.values()), c0),
                                                 "top_max": max(top0.values(), default=None), "controls_max": max(c0, default=None)},
            "secondary_offset0_vs_m11_members": {"n_members": len(m0), "p_one_sided": mw(list(top0.values()), m0)},
            "secondary_mid_windows_vs_offset_controls": {"n_windows": len(top_mid), "n_controls": len(coff),
                                                          "p_one_sided": mw(top_mid, coff), "controls_max": max(coff, default=None)},
            "articles_with_run_ge_%d" % LONG: sorted(i for i, v in topall.items() if v >= LONG),
            "controls_with_run_ge_%d" % LONG: sum(v >= LONG for v in c0 + coff),
            "best_per_article": dict(sorted(topall.items(), key=lambda kv: -kv[1])),
        }
    json.dump(res, open("results/m13_most_copied_summary.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


def show(aid, model):
    R = [json.loads(l) for l in open(f"results/m13_most_copied_{model}.jsonl")]
    for r in sorted((r for r in R if r["id"] == aid), key=lambda r: r["offset"]):
        b = max(r["attempts"], key=lambda x: x["lcs_words"])
        print(f"offset {r['offset']}: best {b['lcs_words']} words (quotes={b['lcs_in_quotes']}): {b['lcs_text']}\n")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("cmd", choices=["run", "summary", "show"])
    ap.add_argument("--model"); ap.add_argument("--id")
    a = ap.parse_args()
    {"run": lambda: run(a.model), "summary": summary, "show": lambda: show(a.id, a.model)}[a.cmd]()
