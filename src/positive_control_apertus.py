"""Positive control on Apertus-8B (Swiss AI, 2025), a model whose training data is published.

Why: our tests found nothing on commercial and open models. Without a model KNOWN to have been trained on La
Vanguardia text we cannot tell "not trained" from "trained but undetectable". Apertus was pretrained on FineWeb-2 /
FineWeb-2-HQ (Spanish included), applying robots.txt opt-outs as of January 2025, when La Vanguardia's news pages were
not opted out. Our FineWeb-2 scan (results/dataset_presence_overlap.json) identifies which of our articles are in
FineWeb-2. (OLMo 2 was tried first and discarded: its training data is English-filtered and contains essentially no
La Vanguardia articles; results/olmo/lookup.jsonl.)

Caveats: (i) Apertus used the Goldfish objective, which suppresses verbatim recall by design, so extraction tests are
not run; this control covers word-probability tests and content (Q->A) recall. (ii) Only 53% of FineWeb-2's Spanish
part was scanned, so "not found" articles are a mix (about a third truly absent): effects are diluted, not inflated.
(iii) FineWeb-2's own filters may select more predictable pages; the 2018 reference model (GPT-2-spanish) calibrates
this, as in M5/M6.

Groups (same period 2011-2023, Spanish): IN = found in FineWeb-2; NOTFOUND = not found in the scanned half.
Post-cutoff controls (2025-26, certainly absent) are a second comparison.
Inputs: results/m5_apertus8b.jsonl, results/m5_lacontra_apertus8b.jsonl (src/m5_logprob.py), reference
results/m5_gpt2es.jsonl, results/m5_lacontra_gpt2es.jsonl, Q->A results/m10_exclusive_Apertus-8B-2509-4bit.jsonl.
Output: results/positive_control_apertus.json
Usage: python -I src/positive_control_apertus.py
"""
import json, os, statistics as st

from scipy.stats import mannwhitneyu
from sklearn.metrics import roc_auc_score

SCORES = (("loss", -1), ("zlib_ratio", -1), ("mink", 1), ("minkpp", 1))  # oriented so that higher = more familiar


def fw2_ids():
    ov = json.load(open("results/dataset_presence_overlap.json"))
    return {k for v in ov["sets"].values() for k in v["hits"]}


def load(p):
    return {(r["id"], r["set"]): r for r in map(json.loads, open(p))} if os.path.exists(p) else {}


def compare(a, b):
    if len(a) < 5 or len(b) < 5:
        return None
    y = [1] * len(a) + [0] * len(b)
    return {"n": [len(a), len(b)], "auc": round(roc_auc_score(y, a + b), 3),
            "p_greater": round(mannwhitneyu(a, b, alternative="greater").pvalue, 4)}


def main():
    inf = fw2_ids()
    lang = {}
    for f in ("members", "lacontra_members", "controls", "lacontra_controls", "lacontra_controls_more"):
        for l in open(f"data/cc/{f}.jsonl"):
            a = json.loads(l)
            lang[a["id"]] = a.get("lang", "es")
    res = {"fw2_spanish_scanned_fraction": 1.0, "logprob": {}}
    # Apertus (known training data) first; then the same split on the open models scored earlier, for comparison
    runs = []
    for m in ("apertus8b", "salamandra7b", "salamandra40b", "alia40b", "llama31_8b", "qwen25_7b", "mistral7b_v03", "gemma2_9b"):
        runs += [(f"{m}/random", f"results/m5_{m}.jsonl", "results/m5_gpt2es.jsonl"),
                 (f"{m}/lacontra", f"results/m5_lacontra_{m}.jsonl", "results/m5_lacontra_gpt2es.jsonl")]
    for tag, tgt, ref in runs:
        T, R = load(tgt), load(ref)
        if not T:
            continue
        out = {}
        groups = {"in": [], "notfound": [], "control": []}
        for (i, s), r in T.items():
            if lang.get(i) != "es":
                continue
            g = "control" if s == "control" else ("in" if i in inf else "notfound")
            groups[g].append((i, s, r))
        for name, sign in SCORES:
            raw = {g: [sign * r[name] for _, _, r in v] for g, v in groups.items()}
            cal = {g: [sign * (r[name] - R[(i, s)][name]) for i, s, r in v if (i, s) in R] for g, v in groups.items()}
            refo = {g: [sign * R[(i, s)][name] for i, s, r in v if (i, s) in R] for g, v in groups.items()}
            out[name] = {"in_vs_notfound": {"target": compare(raw["in"], raw["notfound"]),
                                            "reference_only": compare(refo["in"], refo["notfound"]),
                                            "calibrated": compare(cal["in"], cal["notfound"])},
                         "in_vs_control": {"target": compare(raw["in"], raw["control"]),
                                           "reference_only": compare(refo["in"], refo["control"]),
                                           "calibrated": compare(cal["in"], cal["control"])}}
        out["n_groups"] = {g: len(v) for g, v in groups.items()}
        res["logprob"][tag] = out
    for qa, key in (("results/m10_exclusive_Apertus-8B-2509-4bit.jsonl", "qa_lacontra"),
                    ("results/m10_exclusive_salamandra-7b.jsonl", "qa_lacontra_salamandra7b")):
        if os.path.exists(qa):
            items = {json.loads(l)["item_id"]: json.loads(l) for l in open("data/m10/items.jsonl")}
            rows = [json.loads(l) for l in open(qa)]
            g = {"in": [], "notfound": [], "control": []}
            for r in rows:
                if r["type"] != "qa" or r.get("api_error"):
                    continue
                aid = items[r["item_id"]]["article_id"]
                grp = "control" if r["set"] == "control" else ("in" if aid in inf else "notfound")
                g[grp].append(r)
            res[key] = {k: {"n": len(v), "fact_hits": sum(x["hit"] for x in v),
                            "content_overlap_mean": round(st.mean([x["content_overlap"] or 0 for x in v]), 3) if v else None,
                            "lcs_max": max([x["lcs_words"] for x in v] or [0])} for k, v in g.items()}
    json.dump(res, open("results/positive_control_apertus.json", "w"), indent=1)
    print(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
