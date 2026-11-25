# Pre-registration: replication of the neighbour test inside the Llama-3 vs Llama-3.1 design

Written 2026-11-25, after seeing the first run (results/did_neighbour.json: combined p=0.069 NEW vs NONE,
p=0.065 NEW vs BOTH, effect ≈0.12 SD, direction as predicted) and **before** any replication data was collected.
The git commit of this file timestamps the plan.

**Why a replication and not "more data":** adding articles to the first run until p<0.05 is optional stopping and
inflates false positives. The replication uses only articles not used in the first run and is analysed on its own.

**Data (all disjoint from the first run):**
- NEW2: articles published Apr–Nov 2023 (after Llama 3's, before Llama 3.1's cutoff), from CC-MAIN-2023-50, 2024-10,
  2023-40, same sections and filters as `src/collect_mid2023.sh`, up to 4 per section-month per crawl,
  excluding the 249 first-run articles → `data/cc/mid2023_rep.jsonl`.
- BOTH2: all members published before 2023-03 not sampled in the first run (~445).
- NONE2: all controls not sampled in the first run (~198).

**Procedure (unchanged from the first run):** first ~70-word passage; 3 same-facts rewrites with local
Qwen2.5-7B-Instruct (temp 0.7, same validation); scored with Llama-3.1-8B and Llama-3-8B (MLX 4-bit);
`src/did_neighbour.py`.

**Primary test:** combined equal-weight oriented z-score, one-sided Welch, NEW2 vs NONE2 and NEW2 vs BOTH2,
α = 0.05 each. Prediction if Llama-3.1 was trained on the text: dgap(NEW2) lower (more original-wording gain).
**Checks:** BOTH2 vs NONE2 must be null (p>0.05). Secondary: loss alone (Mann–Whitney). A pooled analysis of both
runs will be reported as secondary, labelled as such.

**Reading:** replication significant and checks clean → evidence that Llama-3.1 gained familiarity with the *wording*
of mid-2023 La Vanguardia articles beyond knowledge of the events. Not significant → the first-run trend is not
confirmed, and we report it as such.
