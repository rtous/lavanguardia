"""Is "found / not found in FineWeb-2" a usable same-period in/out split? Selection check.

Members (2020-2023) are split by whether src/presence_overlap.py found them in FineWeb-2 (full scan). If FineWeb-2's
selection were unrelated to the text, a model that saw neither group (GPT-2-spanish, 2018 data) would not separate
them. AUC is computed only over pairs of the same publication year and section (higher = IN looks more familiar);
p = share of within-stratum label shuffles with AUC <= observed (one-sided, toward "NOT FOUND more familiar").
Output: results/presence_selection_check.json. Usage: python -I src/presence_selection_check.py
"""
import json, re, random
o = json.load(open("results/dataset_presence_overlap.json"))["sets"]["members"]
found = set(o["hits"].keys())
docs = {json.loads(l)["id"]: json.loads(l) for l in open("data/cc/members.jsonl", encoding="utf-8")}
aid = lambda d: (re.search(r"/\d{8}/(\d+)/", d["url"]) or [None, d["id"]])[1]
ref = {r["id"]: r for r in map(json.loads, open("results/m5_gpt2es.jsonl")) if r["set"] == "member"}
def strat_auc(vals):  # vals: id -> score (higher = more familiar); pairs only within (year, section)
    num = den = 0
    for i, d in docs.items():
        if i not in vals or aid(d) not in found: continue
        for j, e in docs.items():
            if j in vals and aid(e) not in found and (d["pub_date"][:4], d["section"]) == (e["pub_date"][:4], e["section"]):
                den += 1; num += (vals[i] > vals[j]) + 0.5 * (vals[i] == vals[j])
    return num / den, den
def perm_p(vals, obs, n=300):
    ids = [i for i in docs if i in vals]; rng = random.Random(0); c = 0
    lab = {i: aid(docs[i]) in found for i in ids}
    for _ in range(n):  # shuffle in/notfound labels within strata
        strata = {}
        for i in ids: strata.setdefault((docs[i]["pub_date"][:4], docs[i]["section"]), []).append(i)
        perm = {}
        for k, v in strata.items():
            l = [lab[i] for i in v]; rng.shuffle(l); perm.update(zip(v, l))
        num = den = 0
        for i in ids:
            if not perm[i]: continue
            for j in ids:
                if not perm[j] and (docs[i]["pub_date"][:4], docs[i]["section"]) == (docs[j]["pub_date"][:4], docs[j]["section"]):
                    den += 1; num += (vals[i] > vals[j]) + 0.5 * (vals[i] == vals[j])
        c += num / den <= obs
    return c / n
res = {"reference_gpt2es_auc": round(strat_auc({i: -r["loss"] for i, r in ref.items()})[0], 3), "models": {}}
for m in ("apertus8b", "salamandra7b", "gemma2_9b", "llama31_8b", "qwen25_7b", "mistral7b_v03"):
    M = {r["id"]: r for r in map(json.loads, open(f"results/m5_{m}.jsonl")) if r["set"] == "member"}
    raw = {i: -M[i]["loss"] for i in M}
    cal = {i: -(M[i]["loss"] - ref[i]["loss"]) for i in M if i in ref}
    a, n = strat_auc(cal)
    res["models"][m] = {"raw_auc": round(strat_auc(raw)[0], 3), "calibrated_auc": round(a, 3), "pairs": n, "p_one_sided": perm_p(cal, a, 200)}
res["n_in"], res["n_notfound"] = sum(aid(d) in found for d in docs.values()), sum(aid(d) not in found for d in docs.values())
json.dump(res, open("results/presence_selection_check.json", "w"), indent=1); print(json.dumps(res, indent=1))
