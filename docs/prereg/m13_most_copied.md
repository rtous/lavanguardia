# Pre-registration: M13, NYT-style extraction of the most-copied La Vanguardia articles

Written 2026-11-28, before any query with this protocol. The git commit of this file timestamps the plan.

**Why.** Verbatim memorization grows with the number of copies of a text in the training data (Carlini et al. 2023;
Kandpal et al. 2022). Our extraction tests (M1, M9, M11) used ordinary articles: in FineWeb-2 the median LV article has
2 near-identical copies. Session 11 found articles copied hundreds of times (`results/fw2_most_copied.md`; top:
*«Nosotros, como el tiempo, también nos desdoblamos»*, 2010-11-09, 1,279 copies). If any LV text has been memorized
by these models, these are the most likely candidates. Copies of LV text on other sites are still LV's text (training
on them is training on LV's works); what has to be excluded is *independent* text, which is why runs inside quotation
marks are excluded and every long run is checked by hand.

**Items (fixed before this test was designed).** The 20 articles of `results/fw2_most_copied.md` (built on
2026-11-27 from FineWeb-2 cluster sizes; error pages and stubs removed by reading the text). Text: the FineWeb-2
document with the largest cluster for each article, i.e. the text as Common Crawl captured it (`data/fw2_top_text.json`,
re-read on 2026-11-28 by `src/fw2_top_check.py`, sha256 `7f3eef1b14f63f246c6a83ffcb0064a8e6316e7dcd9bca41febc6f77ab4d22d8`). Titles in the prompt are the URL slugs.
None of the 20 is in M11's sets (checked by article ID in session 11).

**Models**, same as M11, int4 on a Colab T4, in this order: `BSC-LT/salamandra-7b-instruct`, `Qwen/Qwen2.5-7B-Instruct`,
`meta-llama/Llama-3.1-8B-Instruct` (if an HF token is available). Each is analysed on its own. API models (Gemini,
Claude, GPT…) only by a dated amendment committed before their first query.

**Procedure** (`src/m13_most_copied.py`, fixed before the run): exactly M11's prompt, decoding and scoring
(role-play system prompt, fake assistant turn, 110-word prefix, 1 greedy + 9 samples at T=0.8/top_p=0.95, 256 new
tokens, longest common word run against the next 250 words, quote flag). Seed = article ID + offset.
- *Windows* ("parts of it"): offset 0 with M11's prompt unchanged, then every 300 words while offset + 360 words fit, plus a last window ending at the article's end
  (if it starts at least 60 words after the previous one),
  with the user turn "En un punto del artículo dice así: «…» Continúa…". Articles under 360 words: one window, the
  first 40% of the words as prefix, the rest as the text to match.
- *Offset controls*: the same mid-article prompt at offset 300 on the first 10 La Contra and first 10 random M11
  controls with at least 660 words (published after every tested model's training data).
- Base rate at offset 0: M11's controls on the same model (identical prompt and scoring; 100 per model).

**Primary outcome** per article: best LCS outside quotes over the 10 attempts at offset 0.
**Primary test**, per model: one-sided Mann–Whitney, the 20 most-copied articles > M11's controls,
α = 0.05 / 3 (Bonferroni over the three models). The test for a model is run only once its M11 controls are complete.
**Secondary:** (a) most-copied > M11's members (dose: hundreds of copies vs. a median of 2); (b) mid-article windows >
offset controls; (c) **regurgitation**: any most-copied article with a run of **≥ 25 words** outside quotes, against the
number of controls (offset 0 and offset controls) reaching 25 (M11's control maximum on Salamandra was 8 outside
quotes, 12 with quotes); (d) greedy-only LCS.

**Checks before any run is called La Vanguardia's wording.** Every run ≥ 15 words is shown side by side with the
FineWeb-2 text; checked against the article on lavanguardia.com / the Internet Archive (public pages only); checked
for being a quotation of a third party (e.g. a book by the interviewee) or a stock phrase.

**Reading.**
- Long runs (≥ 25 words) on most-copied articles and none on controls: the model can be made to output La Vanguardia
  wording, which it could only have from training on the article or its copies. Labelled *adversarial* (NYT-style
  prompts), as M11.
- No difference: even the most-copied LV articles are not extractable from these 7–8B models. This bounds
  memorization of the most-exposed LV text for these models; it says nothing about training or about larger models.
