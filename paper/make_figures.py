"""Regenerate paper figures from results/. Run: .venv/bin/python -I paper/make_figures.py"""
import json, os, sys
from collections import defaultdict
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from scipy.stats import mannwhitneyu

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = lambda p: os.path.join(ROOT, "results", p)
OUT = os.path.join(ROOT, "paper", "figures")
BLUE, ORANGE, AQUA = "#2a78d6", "#eb6834", "#1baf7a"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e3de"
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})

def acc(path, key="correct"):
    rows = [json.loads(l) for l in open(R(path))]
    out = {}
    for s in ("member", "control"):
        rs = [r for r in rows if r["set"] == s]
        k, n = sum(r[key] for r in rs), len(rs)
        p = k / n; se = np.sqrt(p * (1 - p) / n)
        out[s] = (p, 1.96 * se)
    return out

M = {"claude-opus-4-5-20251101": "Opus 4.5", "claude-sonnet-4-5-20250929": "Sonnet 4.5", "claude-haiku-4-5-20251001": "Haiku 4.5",
     "gemini-3.1-flash-lite": "Gemini 3.1\nFlash-Lite"}
tests = [("DE-COP, full paraphrases\n(4 options, chance 25%)", "m2_decop_full_v2_{}.jsonl", 0.25, list(M)[:3]),
         ("Pairwise, minimal edits\n(2 options, chance 50%)", "m2b_pairwise_{}.jsonl", 0.50, [list(M)[0], list(M)[1], list(M)[3]])]

# Figure 1: member vs control accuracy
fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.6), gridspec_kw={"width_ratios": [3, 3]})
for ax, (title, pat, chance, models) in zip(axes, tests):
    for i, m in enumerate(models):
        a = acc(pat.format(m))
        for j, (s, col, mk) in enumerate((("member", BLUE, "o"), ("control", ORANGE, "s"))):
            p, e = a[s]
            ax.errorbar(i + (j - 0.5) * 0.28, p, yerr=e, fmt=mk, color=col, ms=6, capsize=0, lw=1.5,
                        mec="white", mew=1, label={"member": "Members (pre-cutoff)", "control": "Controls (post-cutoff)"}[s] if i == 0 else None)
    ax.axhline(chance, color=INK2, lw=1, ls=(0, (3, 3)))
    ax.text(-0.55, chance + 0.02, "chance", color=INK2, fontsize=8, ha="left")
    ax.set_xticks(range(len(models))); ax.set_xticklabels([M[m] for m in models])
    ax.set_xlim(-0.6, len(models) - 0.4); ax.set_ylim(0, 1)
    ax.yaxis.set_major_formatter(matplotlib.ticker.PercentFormatter(1.0))
    ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
    ax.set_title(title, fontsize=9, color=INK)
axes[0].set_ylabel("Original picked")
axes[0].legend(frameon=False, loc="lower left", fontsize=8)
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_recognition.pdf")); plt.close(fig)

# Figure 2: logprob AUCs with bootstrap CI
def load(p): return {(r["id"], r["set"]): r for r in map(json.loads, open(R(p)))}
tgt, ref = load("m5_qwen25_7b.jsonl"), load("m5_gpt2es.jsonl")
keys = sorted(set(tgt) & set(ref)); mk = [k for k in keys if k[1] == "member"]; ck = [k for k in keys if k[1] == "control"]
SIGN = {"loss": -1, "zlib_ratio": -1, "mink": 1, "minkpp": 1}
LAB = {"loss": "Loss", "zlib_ratio": "zlib ratio", "mink": "Min-K%", "minkpp": "Min-K%++"}
rng = np.random.default_rng(0)
def auc_ci(f, s):
    pos = s * np.array([f(k) for k in mk]); neg = s * np.array([f(k) for k in ck])
    a = mannwhitneyu(pos, neg).statistic / (len(pos) * len(neg))
    b = [mannwhitneyu(x, y).statistic / (len(x) * len(y)) for x, y in
         ((rng.choice(pos, len(pos)), rng.choice(neg, len(neg))) for _ in range(500))]
    return a, np.percentile(b, 2.5), np.percentile(b, 97.5)
fig, ax = plt.subplots(figsize=(6.6, 2.9))
series = [("Qwen2.5-7B (target)", BLUE, "o", lambda m: (lambda k: tgt[k][m])),
          ("GPT-2-spanish, 2018 data (drift baseline)", ORANGE, "s", lambda m: (lambda k: ref[k][m])),
          ("Calibrated (target − baseline)", AQUA, "D", lambda m: (lambda k: tgt[k][m] - ref[k][m]))]
table = []
for i, met in enumerate(SIGN):
    for j, (lab, col, mkr, f) in enumerate(series):
        a, lo, hi = auc_ci(f(met), SIGN[met]); table.append((met, lab, a, lo, hi))
        ax.errorbar(i + (j - 1) * 0.24, a, yerr=[[a - lo], [hi - a]], fmt=mkr, color=col, ms=6, lw=1.5,
                    mec="white", mew=1, label=lab if i == 0 else None)
ax.axhline(0.5, color=INK2, lw=1, ls=(0, (3, 3))); ax.text(-0.45, 0.452, "no signal = 0.5", color=INK2, fontsize=8, ha="left")
ax.set_xticks(range(4)); ax.set_xticklabels([LAB[m] for m in SIGN]); ax.set_ylim(0.44, 0.64); ax.set_xlim(-0.5, 3.5)
ax.set_ylabel("AUC (member vs control)"); ax.grid(axis="y", color=GRID, lw=0.6); ax.set_axisbelow(True)
ax.legend(frameon=False, fontsize=8, loc="lower center", ncol=2, bbox_to_anchor=(0.5, 1.0))
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_logprob_auc.pdf")); plt.close(fig)
json.dump(table, open(os.path.join(OUT, "logprob_auc_table.json"), "w"), indent=1)
print("figures written", len(mk), len(ck))

# Figure: M10 URL-ID-as-date. How far (in days) the date implied by the model's predicted article ID is from the
# true publication date. Members 2021-2023 (7-8 digit IDs) vs post-cutoff controls.
sys.path.insert(0, os.path.join(ROOT, "src"))
_cwd = os.getcwd(); os.chdir(ROOT)
import datetime as _dt
from m10_exclusive_facts import id_to_date_fn
_err = id_to_date_fn()
_items = {i["item_id"]: i for i in map(json.loads, open(os.path.join(ROOT, "data/m10/items.jsonl")))}
M10 = [("gemini-3.1-flash-lite", "Gemini 3.1 Flash-Lite"), ("gemma-2-9b-4bit", "Gemma-2-9B (base)"),
       ("Meta-Llama-3.1-8B-4bit", "Llama-3.1-8B (base)")]
fig, axes = plt.subplots(1, len(M10), figsize=(6.6, 2.4), sharey=True)
for ax, (m, lab) in zip(axes, M10):
    rows = {r["item_id"]: r for r in map(json.loads, open(R(f"m10_exclusive_{m}.jsonl"))) if not r.get("api_error")}
    for st, col, mk in (("member", BLUE, "o"), ("control", ORANGE, "s")):
        xs, ys = [], []
        for r in rows.values():
            if r["type"] != "url_id" or r["set"] != st:
                continue
            it = _items[r["item_id"]]
            e = _err(r["pred"][0] if r["pred"] else None, r["answer"], it["pub_date"])
            if e is None:
                continue
            d = it["pub_date"]
            xs.append(_dt.date(int(d[:4]), int(d[4:6]), int(d[6:8])))
            ys.append(min(max(e, 0.5), 5000))
        ax.scatter(xs, ys, s=10, color=col, marker=mk, alpha=0.8, lw=0,
                   label="members (2021-23)" if st == "member" else "controls (2025-26)")
    ax.set_yscale("log"); ax.set_title(lab, fontsize=9)
    for y, t in ((1, "1 day"), (30, "1 month"), (365, "1 year")):
        ax.axhline(y, color=GRID, lw=0.8, zorder=0); ax.text(_dt.date(2021, 1, 1), y * 1.15, t, fontsize=6.5, color=INK2)
    ax.axhline(5000, color=INK2, lw=0.6, ls=":")
    ax.tick_params(axis="x", labelsize=7, rotation=45)
axes[0].set_ylabel("error of implied date (days)")
axes[0].text(_dt.date(2021, 1, 1), 5600, "no valid ID", fontsize=6.5, color=INK2)
axes[-1].legend(fontsize=7, frameon=False, loc="center right")
fig.tight_layout(); fig.savefig(os.path.join(OUT, "fig_m10_urlid.pdf")); plt.close(fig)
os.chdir(_cwd)
