# Pre-registration: M13c, does the Garnier signal generalize? Dense probe of the next most-copied *La Contra* interviews

Written 2026-11-28 ~12:35 UTC, before any query with this protocol. The git commit of this file timestamps the plan.

**Why.** M13b (`docs/prereg/m13b_garnier_dense.md`) found that Claude Opus 4.5 reproduces more of the wording of the
most-copied LV article (the Garnier *La Contra* interview, 1,279 FineWeb-2 copies) than of 4 comparable unseen
interviews (window-level p = 0.0046), but on one article only, so the article-level evidence is 1 vs 4. M13c asks
whether the same holds for the other *La Contra* interviews among the 20 most-copied articles, with enough articles to
test at the article level. Garnier itself, which generated the hypothesis, is **not** in the primary test.

**Members (fixed by `results/fw2_most_copied.md`, 2026-11-27).** The three other *La Contra* interviews in the top 20:
#2 Juan Gérvas (54365145790, 2013, 490 copies, 874 words), #3 "No se olvide de apagar el wi-fi por la noche"
(54228364832, 2011, 373 copies, 884 words), #18 Catherine L'Ecuyer (54360763481, 2013, 247 copies, 824 words). Text
from `data/fw2_top_text.json` (sha256 7f3eef1b…, as in M13/M13b).

**Controls.** 8 *La Contra* interviews published Feb–Mar 2026 (after both models' training data): M13b's 4
(11458911, 11460053, 11478598, 11479519; their M13b rows are reused, same protocol and model) plus the next 4 of M13's
*La Contra* offset-control list (11461087, 11480309, 11461945, 11462840; 773–858 words), queried now.

**Models.** Primary: `claude-opus-4-5-20251101`. Secondary: `gemini-3.1-flash-lite`.

**Procedure.** Exactly M13b's (`src/m13b_garnier.py` functions, called from `src/m13c_lacontra.py`): M13's prompts,
110-word prefixes every 50 words while ≥ 50 words follow, 3 attempts per window (Claude default decoding; Gemini
attempt 1 at T=0, attempts 2–3 at T=0.8/top_p 0.95, seed = ID + offset + i), score = longest run against the article
outside the prompt window, quote flag as M11. New windows: members 44, new controls 55 (99 × 3 = 297 calls per model).
Evidence: `evidence/m13c_lacontra/calls.jsonl`.

**Primary test (article level), per model.** Per article: the median over its windows of the best run outside quotes.
One-sided Mann–Whitney, 3 members > 8 controls, α = 0.05 for Claude (smallest attainable p = 1/165 ≈ 0.006).
**Secondary:** (a) window level, the 3 members' windows > the 8 controls' windows (one-sided MW); (b) windows with a run
≥ 12 words, members vs controls; (c) the same article-level test with Garnier added (4 vs 8; Garnier is not
independent of the hypothesis, so this is reported, not tested for confirmation); (d) Gemini as above.

**Checks.** Every run ≥ 12 words is shown side by side with the original and checked for being a quotation, a stock
phrase, or the interviewee's own published wording, before it is described as LV's text.

**Reading.** Members above controls at the article level: Claude holds fragments of the wording of LV's most-copied
interviews, not just of one, consistent with copy-count-driven memorization (adversarial prompts, labelled as such).
No difference: the Garnier result does not generalize to the next most-copied interviews (copies 247–490); it stays a
single suspicious case.

**Cost.** ≈ US$2.6 on Claude Opus 4.5; cents on Gemini.
