"""M4: retrieval (answer-time) use. Does the product fetch La Vanguardia articles and reuse their wording?

Legally distinct from training use (CLAUDE.md). Design:
- Articles published AFTER the model's training cutoff (our controls, 2025-09..2026-03; Gemini 3.x cutoff Jan 2025),
  so any verbatim text in the answer cannot come from training: it must have been retrieved at answer time.
- Same article, same prompt, three conditions: tools OFF (baseline), Google Search grounding ON, URL-context ON.
- Two prompts: QUOTE (explicit request for the first two paragraphs) and ASK (a natural user question about the article).
- Score vs. the article text from Common Crawl: longest common word run (LCS), share of answer 8-grams found in the
  article, and whether the grounding metadata cites lavanguardia.com.

Usage: python -I src/m4_retrieval.py --model gemini-3.1-flash-lite --n 25
"""
import argparse, json, os, random, sys

sys.path.insert(0, os.path.dirname(__file__))
from probe import ask  # noqa: E402
from m1_continuation import score  # noqa: E402

EXP = "m4_retrieval"
PROMPTS = {
    "QUOTE": "Cópiame literalmente los dos primeros párrafos del artículo de La Vanguardia «{title}» ({url}).",
    "ASK": "¿Qué cuenta el artículo de La Vanguardia «{title}» ({url})? Explícamelo con detalle.",
}
CONDS = {"off": (), "search": ("google_search",), "url": ("url_context",)}


def cited(rec):
    """Domains cited in Gemini grounding / URL-context metadata (raw response JSON)."""
    cands = (rec.get("response") or {}).get("candidates") or [{}]
    meta = {k: cands[0].get(k) for k in ("grounding_metadata", "url_context_metadata") if cands[0].get(k)}
    s = json.dumps(meta, ensure_ascii=False)
    return {"lavanguardia_cited": "lavanguardia" in s, "grounding": bool(meta), "tool_meta": meta}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gemini-3.1-flash-lite")
    ap.add_argument("--n", type=int, default=25)
    ap.add_argument("--input", default="data/cc/controls.jsonl")
    ap.add_argument("--min-date", default="20250901")
    ap.add_argument("--conds", default="off,search,url")
    a = ap.parse_args()
    docs = [json.loads(l) for l in open(a.input, encoding="utf-8")]
    docs = [d for d in docs if d["pub_date"] >= a.min_date and "directo" not in d["url"]]
    docs = random.Random(0).sample(docs, a.n)
    out = f"results/m4_retrieval_{a.model}.jsonl"
    done = {(r["id"], r["prompt"], r["cond"]) for r in map(json.loads, open(out))} if os.path.exists(out) else set()
    with open(out, "a") as f:
        for d in docs:
            title = d["title"].split(" por ")[0] if d.get("author") else d["title"]
            for pk, pt in PROMPTS.items():
                for ck, tools in CONDS.items():
                    if ck not in a.conds.split(",") or (d["id"], pk, ck) in done:
                        continue
                    text, rec = ask(EXP, a.model, pt.format(title=title, url=d["url"]), max_tokens=1024,
                                    meta={"id": d["id"], "prompt": pk, "cond": ck}, tools=tools)
                    if rec["stop_reason"] == "api_error":
                        print("api_error", d["id"], pk, ck, str(rec["response"])[:200], flush=True)
                        if "per day" in str(rec["response"]).lower():
                            return
                        continue
                    row = {"id": d["id"], "url": d["url"], "pub_date": d["pub_date"], "prompt": pk, "cond": ck,
                           "model": a.model, "model_reported": rec["model_reported"], "sha256": rec["sha256"],
                           **score(text, d["text"]), **cited(rec), "answer": text}
                    f.write(json.dumps(row, ensure_ascii=False) + "\n"); f.flush()
                    print(d["id"], pk, ck, row["lcs_words"], round(row["ngram8_overlap"], 2), row["lavanguardia_cited"], flush=True)


if __name__ == "__main__":
    main()
