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

## Deviations (approved by the investigator 2026-11-26; written and committed before any replication scoring)
Status when written: 247 of ~810 rewrites existed (MLX), no replication passage had been scored by any model.
The laptop (Apple Silicon, MLX) was replaced by Google Colab (NVIDIA T4, 15 GB), where MLX does not run.
1. **Backend.** Same models, run with Hugging Face transformers instead of MLX: rewriter `Qwen/Qwen2.5-7B-Instruct`,
   scorers `meta-llama/Llama-3.1-8B` and `meta-llama/Meta-Llama-3-8B`, all in bitsandbytes nf4 4-bit (the closest
   available to the registered MLX 4-bit; bf16 does not fit a T4). Same scoring function, passage rule, prompt,
   temperature 0.7 / top_p 0.95 and validation rule; at most 9 samples per passage, drawn 3 per round.
2. **All rewrites regenerated with the new backend** (`data/decop/paraphrases_mid2023_rep_hf.jsonl`), including the
   247 made with MLX, which are kept unchanged and unused. Reason: completing the set with a different backend would
   make NEW2 rewritten entirely by MLX and NONE2 entirely by transformers, so any backend difference in rewrite style
   would be confounded with the group contrast that the test measures.
3. **NEW2 frozen at the 168 fresh articles already collected**; the Common Crawl fetch is not rerun.
Primary test, checks and reading are unchanged. The pooled analysis with the first run (MLX) stays secondary; it now
also mixes backends, which will be stated.
