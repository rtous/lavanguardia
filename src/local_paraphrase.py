"""Generate same-facts rewrites locally (no API) for the neighbour test inside the Llama 3 vs 3.1 design.

Groups: NEW = all mid-2023 articles (data/cc/mid2023.jsonl, seen only by Llama 3.1), BOTH = random members published
before 2023-03 (seen by both), NONE = random controls (seen by neither). Passage = first ~70 words (same rule as DE-COP).
Rewriter: a local instruct model of a DIFFERENT family than the scored models (default Qwen2.5-7B-Instruct), so the
rewrites are not in Llama's own style. 3 rewrites per passage, sampled (temp 0.7). Resumable.

Usage: python -I src/local_paraphrase.py --out data/decop/paraphrases_mid2023.jsonl [--n-both 250 --n-none 250]
"""
import argparse, json, os, random, re, sys

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

sys.path.insert(0, os.path.dirname(__file__))
from m2_decop import passage  # noqa: E402

PROMPT = """Reescribe el siguiente fragmento periodístico en español. Conserva exactamente el mismo significado, los mismos datos y nombres propios y una longitud similar, pero con una redacción claramente diferente (otro orden, otras palabras). No añadas ni quites información. Devuelve solo el texto reescrito, sin comentarios.

Fragmento:
{p}"""


def ok(orig, t):
    """Reject drift into other scripts, meta-comments and rewrites of very different length."""
    if re.search(r"[\u0400-\u04ff\u3040-\u30ff\u4e00-\u9fff\uac00-\ud7af]", t) or "\n\n" in t:
        return False
    r = len(t.split()) / max(1, len(orig.split()))
    return 0.6 <= r <= 1.5 and t != orig


def items(n_both, n_none, seed=0):
    rd = lambda f: [json.loads(l) for l in open(f, encoding="utf-8")]
    rng = random.Random(seed)
    new = [(d, "member", "NEW") for d in rd("data/cc/mid2023.jsonl")]
    both = [d for d in rd("data/cc/members.jsonl") if d["pub_date"] < "20230301"]
    none = rd("data/cc/controls.jsonl")
    return new + [(d, "member", "BOTH") for d in rng.sample(both, n_both)] + [(d, "control", "NONE") for d in rng.sample(none, n_none)]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="mlx-community/Qwen2.5-7B-Instruct-4bit")
    ap.add_argument("--out", required=True)
    ap.add_argument("--n-both", type=int, default=250); ap.add_argument("--n-none", type=int, default=250)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    model, tok = load(a.model)
    sampler = make_sampler(temp=0.7, top_p=0.95)
    done = {(r["id"], r["group"]) for r in map(json.loads, open(a.out))} if os.path.exists(a.out) else set()
    todo = [x for x in items(a.n_both, a.n_none) if (x[0]["id"], x[2]) not in done]
    if a.limit:
        todo = todo[: a.limit]
    with open(a.out, "a") as f:
        for i, (d, s, g) in enumerate(todo):
            p = passage(d["text"])
            msgs = [{"role": "system", "content": "Eres un corrector de estilo. Respondes siempre y solo en español."},
                    {"role": "user", "content": PROMPT.format(p=p)}]
            prompt = tok.apply_chat_template(msgs, add_generation_prompt=True, tokenize=False)
            outs, tries = [], 0
            while len(outs) < 3 and tries < 9:
                tries += 1
                t = generate(model, tok, prompt=prompt, max_tokens=300, sampler=sampler).strip()
                t = re.sub(r"^(Fragmento reescrito|Texto reescrito)\s*:\s*", "", t, flags=re.I).strip().strip('"')
                if ok(p, t):
                    outs.append(t)
            if len(outs) < 3:
                print("skip", d["id"], flush=True)
                continue
            f.write(json.dumps({"id": d["id"], "set": s, "group": g, "pub_date": d["pub_date"], "title": d.get("title", ""),
                                "passage": p, "paraphrases": outs, "para_model": a.model}, ensure_ascii=False) + "\n")
            f.flush()
            if i % 20 == 0:
                print(i, len(todo), g, flush=True)


if __name__ == "__main__":
    main()
