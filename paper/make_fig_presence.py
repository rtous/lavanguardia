"""Figure: La Vanguardia pages in FineWeb-2 (Spanish) by Common Crawl year and by publication year.
Input results/dataset_presence_by_year.json (src/presence_by_year.py). Run: python -I paper/make_fig_presence.py"""
import json, os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BLUE, INK, INK2, GRID = "#2a78d6", "#0b0b0b", "#52514e", "#e4e3de"  # same tokens as make_figures.py
plt.rcParams.update({"font.family": "serif", "font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK,
                     "xtick.color": INK2, "ytick.color": INK2, "axes.spines.top": False, "axes.spines.right": False})
d = json.load(open(os.path.join(ROOT, "results", "dataset_presence_by_year.json")))["spa_Latn"]
crawl = d["by_crawl_year"]
pub = {k: v for k, v in d["by_publication_year"].items() if k.isdigit() and int(k) <= 2026}
old = sum(v for k, v in pub.items() if int(k) <= 2010)
pub = {"≤2010": old, **{k: v for k, v in pub.items() if int(k) > 2010}}

fig, axes = plt.subplots(1, 2, figsize=(6.8, 2.5), sharey=True, gridspec_kw={"width_ratios": [len(crawl), len(pub)]})
panels = ((axes[0], crawl, "Year of the Common Crawl capture"), (axes[1], pub, "Year the article was published"))
for ax, series, xlabel in panels:
    xs, ys = list(series), [v / 1000 for v in series.values()]
    ax.bar(range(len(xs)), ys, width=0.72, color=BLUE, edgecolor="white", linewidth=1)
    ax.set_xticks(range(len(xs)), ["≤’10" if x == "≤2010" else "’" + x[2:] for x in xs], fontsize=7.5)
    ax.set_xlabel(xlabel)
    ax.yaxis.grid(True, color=GRID, lw=0.6); ax.set_axisbelow(True); ax.tick_params(length=0)
    i = max(range(len(ys)), key=ys.__getitem__)  # label only the peak
    ax.annotate(f"{series[xs[i]]:,}", (i, ys[i]), xytext=(0, 3), textcoords="offset points", ha="center",
                fontsize=7.5, color=INK)
axes[0].set_ylabel("Pages (thousands)")
fig.tight_layout()
out = os.path.join(ROOT, "paper", "figures", "fig_fineweb2_presence.pdf")
fig.savefig(out); fig.savefig(out.replace(".pdf", ".png"), dpi=110)
print(out)
