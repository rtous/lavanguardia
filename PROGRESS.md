# PROGRESS

## 2026-11-24 — Session 1: setup + literature review
**Done**
- Created `CLAUDE.md` (goals, ground rules, layout) and `docs/literature_review.md` (cases + methods).
- Reviewed precedents. The key one is **GEMA v. OpenAI (Munich, 11 Nov 2025)**: memorization = reproduction, and the TDM exception was rejected.
  Also reviewed NYT v. OpenAI (Exhibit J regurgitation), Bartz v. Anthropic, Kadrey v. Meta, and Getty v. Stability.
- Decision: **no paywall circumvention or "hacking" of the archive**, because it risks inadmissibility and liability. Legal sources instead.
- Found that **lavanguardia.com articles are in Common Crawl** (checked CC-MAIN-2019-09 and 2023-14), so we can start with
  real La Vanguardia text now, legally, without waiting for the licensed corpus.
- Current robots.txt blocks GPTBot/ClaudeBot/CCBot/Bytespider, and `llms.txt` has a legal block.

**Candidate methods (shortlist, ranked for court use)**
1. **M1 Verbatim continuation**: prefix → continuation, scored with longest common substring / ROUGE-L. This mirrors GEMA and NYT Exhibit J. Primary method.
2. **M2 DE-COP multiple choice**: verbatim passage vs. paraphrases, with a statistical test against 25% chance and against post-cutoff controls.
3. **M3 Cloze of exclusive details**: quotes, names and figures unique to an article (interviews, scoops).
4. **M4 Retrieval/RAG test**: browsing-enabled products with paywalled articles. Tests current use, as a separate claim.
5. **M5 Logprob methods** (Min-K%++, dataset inference): only for models exposing logprobs, or open-weight
   models as a calibration sanity check.
6. **M6 Copyright traps**: recommend to La Vanguardia **now** for future articles. It gives the strongest future evidence.
Supporting facts: Common Crawl presence by date, and robots.txt opt-out history from the Wayback Machine.

**Next steps**
- [ ] Get the Wayback Machine history of lavanguardia.com/robots.txt to date the AI opt-out.
- [ ] Use the Common Crawl index to build a sample (~200–500) of La Vanguardia articles with known crawl dates and pre-cutoff
      publication dates, plus post-cutoff controls (same sections). Store WARC offsets for provenance.
- [ ] Set up `src/` with provider clients (OpenAI, Anthropic, Google, Mistral…) and the evidence logger (JSONL + SHA-256).
- [ ] Pilot M1 + M2 on ~50 articles × 3 models. Compare with a known-memorized proxy (e.g., NYT examples) to calibrate.
- [ ] Decide with the user/legal team which models and jurisdictions matter most (needed for the cutoff dates).

**Answers from the user (session 1)**
- Acting **for Grupo Godó**, so the corpus and traps are possible later.
- Targets: all main providers. **Start with the ones with the fewest barriers.**
- Current phase is a **viability assessment**. Court formalities come later, if it is viable.

## 2026-11-24 — Session 1b: data pipeline + robots.txt history
**Done**
- `.venv` (requests, warcio, trafilatura). `data/` is gitignored.
- `src/cc_fetch.py`: pulls La Vanguardia articles from the Common Crawl index, with WARC provenance and SHA-256.
  Pilot: 10 articles (internacional, 2022) from CC-MAIN-2023-14 → `data/cc/CC-MAIN-2023-14.jsonl`. **Full body text
  is present**, including signed correspondent pieces. The Common Crawl index server gives frequent 503s, and the retry handles it.
- `src/robots_history.py` + `results/robots_wayback_snapshots.json`. Findings (details in docs/literature_review.md §3):
  AI bots were blocked only from /peliculas-series/ and /libros/ from 2024-04-25; the **full block of GPTBot/ClaudeBot/CCBot/Bytespider started 2026-03-17**.
  Article pages had no TDM meta tags. The legal angle is to be discussed with counsel. It strengthens the case for memorization-based evidence.
- No API keys are present on the machine (checked env).

**Provider priority (fewest barriers first)**
1. **Open-weight models from commercial providers** (Meta Llama 3.x, Mistral, Qwen, DeepSeek, Gemma) run locally (M3 16GB:
   7–8B quantized) or via hosted APIs. They have full logprobs and no regurgitation filters. They are good for calibrating all methods, and they are
   commercial AI in their own right (Meta AI, Le Chat run on them).
2. **OpenAI API**: logprobs on non-reasoning models (gpt-4o, gpt-4.1), older models are still callable, Common Crawl is documented in GPT-3.
3. **Mistral API, DeepSeek API** (weak output filters).
4. **Gemini, Claude** (no logprobs on Claude, stronger anti-regurgitation filters), so black-box methods only.
- A single **OpenRouter** key covers most of these, which is the simplest start.

**Next steps**
- [ ] Get API keys from the user (OpenRouter and/or OpenAI) into `.env`.
- [ ] Scale cc_fetch to ~300 pre-cutoff articles from several crawls/sections (favor high-circulation and opinion pieces, which are copied
      more widely and memorized more), plus ~300 post-cutoff controls (2026 articles, fetched from Common Crawl 2026 crawls or the Godó corpus).
- [ ] Build `src/probe.py` (provider-agnostic client + JSONL evidence log) and `src/m1_continuation.py`, `src/m2_decop.py`.
- [ ] Pilot local open-weight model (Ollama/llama.cpp) with Min-K%++ and M1 as a free sanity check.

## 2026-11-24 — Session 1c: informal self-test (Claude Opus 5.5, in-session)
- M1 (verbatim continuation) on 4 unseen 2022 internacional articles, 50-word prefix → `evidence/self_pilot/continuations.json`.
- **Result: negative for verbatim recall.** Longest common run was 1–4 words, with 0% 5-gram overlap. The model knew the *facts*
  (Mazars dropping Trump, Russia's recognition of Donetsk/Lugansk) but not the *wording*.
- The 4-word match ("hasta la firma de") came from article 8, which reads like agency copy (EFE/Europa Press).
- Not usable as evidence: no API log, informal, small n. Same model via the Anthropic API would be the proper version.
- **Lessons:**
  1. Ordinary news articles are rarely memorized verbatim by frontier models. M1 will only work on **highly duplicated** pieces
     (famous columns and interviews, widely reposted texts), so select articles for that.
  2. **Knowing the facts is not evidence**, because they appear in many sources. We need wording-level signals: DE-COP (M2) and logprob
     methods (M5) are more sensitive than M1.
  3. **Exclude agency wire copy** (EFE, Europa Press, Reuters…), since it appears in many outlets. Use signed, exclusive La Vanguardia content.
  4. cc_fetch needs a **language/quality filter**: one lavanguardia.com URL in Common Crawl contained a Japanese spam page.

## 2026-11-24 — Session 2: first real experiments (Anthropic API + local models)
**Setup**
- Anthropic API via the `ant auth login` profile (no key in `.env` needed). Models available include the Claude 4.5 family:
  Sonnet 4.5 (training data to Jul 2025, **retires 2026-11-30**), Haiku 4.5 (Jul 2025), Opus 4.5 (Aug 2025).
  The 5.x models have Jun 2026 cutoffs, so there are no clean controls for them yet (we'd need articles from after Jun 2026, i.e. the Godó corpus).
- Since API version 2026-10-21, `temperature` is rejected, so outputs are not deterministic. This is noted in the logs.
- `src/probe.py`: every call is logged to `evidence/<exp>/calls.jsonl` with request id, model, full request/response and SHA-256.
- `src/cc_fetch.py` v2: per-year index queries, filters for language, byline, agency copy and length, and round-robin sampling across months.
  `src/collect.sh members|controls`. **Data: 695 members (published 2020-01..2023-02, crawls 2022-33/2023-14/2023-50)
  and 448 controls (published 2025-09..2026-03, crawls 2025-51..2026-12)**, all signed, non-agency, Spanish.
- Confirmed: CC-MAIN-2026-12 (Mar 2026) has La Vanguardia captures and CC-MAIN-2026-17 has **none**, so CCBot obeyed the 2026-03-17 block.
- Cost so far: about **$18** for 6,220 API calls.

**Results (pilot: 60 members + 60 controls for API tests, all 1,143 articles for logprobs)**

| Test | Model | Members | Controls | Verdict |
|---|---|---|---|---|
| M1 continuation (60-word prefix, neutral prompt) | Opus 4.5 | median LCS 3 words, max 9 | median 3, max 9 | no signal |
| M1 | Sonnet 4.5 | median 3, max 10 | median 3, max 7 | no signal |
| M2 DE-COP 4-choice, full paraphrases | Opus 4.5 | 86.7% | 80.8% | n.s. (p=0.15) |
| M2 | Sonnet 4.5 | 72.5% | 73.3% | no signal |
| M2 | Haiku 4.5 | 41.2% | 34.2% | weak, n.s. (p=0.09) |
| M2 4-choice, minimal edits | all | 78–94% | 85–97% | **invalid design** (see below) |
| M2b pairwise, minimal edits (chance 50%) | Opus 4.5 | 74.4% | 82.2% | no signal |
| M2b | Sonnet 4.5 | 71.1% | 73.2% | no signal |
| M5 Min-K% (logprobs), raw | Qwen2.5-7B (local) | | | AUC 0.560 [0.525,0.597], p=3e-4 |
| M5 Min-K%, drift baseline | GPT-2-spanish (data 2018, has seen neither set) | | | AUC 0.533, p=0.03 |
| M5 Min-K%, reference-calibrated (Qwen − GPT-2) | | | | AUC 0.534 [0.499,0.569], p=0.025 (loss: 0.542, p=0.008) |

**Interpretation / lessons**
1. **No evidence that the Claude 4.5 models memorized randomly sampled La Vanguardia articles.** Verbatim continuation finds
   at most about 10 common words, which are generic phrases, on both members and controls.
2. **DE-COP-style tests are confounded with frontier models.** They pick the human original well above chance *even on
   unseen controls*, because they detect LLM-written paraphrases. Only the member-vs-control *difference* is evidence.
   A 4-choice test with minimal edits is **invalid**: the original is the consensus of the 3 variants, so it can be found by majority vote.
   The pairwise version fixes that, but the edits are still detectable.
3. **Logprob methods on an open-weight model give a weak but real-looking signal.** Qwen2.5-7B finds pre-2024 La Vanguardia text more
   predictable. Part of it is temporal drift, as the 2018-data baseline shows a smaller gap. After calibration a small residual remains
   (AUC ≈0.53–0.54, p≈0.01–0.03). That is weak per article, but dataset-level aggregation over thousands of articles (Maini et al.) could
   make it significant. It does not yet tell a judge anything.
4. **Viability so far:** demonstrating *training* use on *ordinary* articles is hard with today's frontier models. Paths
   that could still work:
   a. **Highly duplicated content** (La Contra interviews, star columnists, editorials and viral pieces that are copied across the web).
      Memorization grows with the number of duplicates (Carlini 2023). This is the GEMA analogue.
   b. **Dataset inference with large N** (the Godó corpus) on open-weight and logprob-exposing models (OpenAI gpt-4.1 / 4o).
   c. **Retrieval / current use** (ChatGPT search, Perplexity, Claude with web search): does the product fetch and reproduce
      paywalled La Vanguardia text? This is legally distinct but probably the easiest to show convincingly.
   d. **Copyright traps** in future articles.

**Next steps**
- [ ] Build a "high-duplication" sample (La Contra, top columnists, editorials) and rerun M1 and M2b on the Claude 4.5 models (Sonnet 4.5 retires 2026-11-30, so do this first).
- [ ] Get an OpenAI key: gpt-4.1/4o logprobs allow M5 on a commercial frontier model, and GPT-3-era models were documented as trained on Common Crawl.
- [ ] Retrieval test (M4) design: web-search-enabled products and paywalled articles.
- [ ] Implement dataset inference (aggregate several MIA features, t-test) on Qwen and others.
- [ ] Commit code and docs (ask the user first). `data/` stays out of git; decide whether `evidence/` goes in git (good for custody, but it contains article text).

## 2026-11-24 — Session 3: paper draft, Gemini, La Contra
**Done**
- `paper/`: research-paper-style draft (`paper.tex` → `paper.pdf`, figures from `paper/make_figures.py`). Covers sessions 1–2.
- **Gemini**: key stored in `.env` (gitignored). `probe.py` supports `gemini-*` (google-genai, v1beta, temperature 0, logged like Anthropic).
  - Gemini 2.5 models: "no longer available to new users". Pro models give 429 (free-tier key, no billing).
  - **Logprobs are not enabled** for any accessible Gemini model ("Logprobs is not enabled for this model"), so only black-box tests are possible.
  - Usable: `gemini-3.1-flash-lite` (knowledge cutoff Jan 2025, so our controls are valid) and `gemini-3-flash-preview`
    (Gemini 3 family, cutoff Jan 2025, but its free-tier daily quota is very small).
  - M1 on gemini-3.1-flash-lite (60+60): members median LCS 3, max 7; controls median 3, max 11 (a generic "la gran triunfadora
    de la 31ª edición de los premios Forqué"). **No signal.**
  - M2b pairwise on flash-lite: running (slow, rate-limited); results in `results/m2b_pairwise_gemini-3.1-flash-lite.jsonl`.
- **High-duplication sample: La Contra** (`src/collect_lacontra.sh`): 212 members (2011–2023) and 41 controls (2025-09..2026-03).
  Few controls exist because 2025–26 crawls have few La Contra captures. For M1 that matters little: long verbatim runs are
  self-evident memorization, and controls only give the base rate.
  - M1 on La Contra (results `results/m1_continuation_lacontra_*.jsonl`): Sonnet 4.5 (n=65), Opus 4.5 (70), Haiku 4.5 (100),
    **Opus 5.5 (99), Sonnet 5.5 (100)**: max LCS 6–8 words, 0% 8-gram overlap, all generic phrases. No refusals (the models write
    real continuations of 130–180 words). **No verbatim memorization even of La Contra.**
- Scripts take `--tag` (sample name) and `--inputs`; failed API calls are no longer written as results.
- **Anthropic credit exhausted** (about $20 spent in total), so the remaining Claude calls failed with 400 "credit balance too low".
  Top up before continuing. Sonnet 4.5 retires 2026-11-30.

**Updated assessment**
Across 7 commercial models (Claude Haiku/Sonnet/Opus 4.5, Opus/Sonnet 5.5, Gemini 3.1 Flash-Lite, partial Gemini 3 Flash), neither
ordinary articles nor La Contra interviews are reproduced verbatim from a neutral 60-word prompt. Per-article "regurgitation" evidence
in the GEMA/NYT style does not look obtainable for this newspaper with these models. Remaining routes, ranked:
1. **Retrieval-time use** (web-enabled ChatGPT / Gemini / Claude / Perplexity reproducing paywalled articles). This is testable now.
2. **Dataset inference** with the Godó corpus (thousands of articles), on models that expose logprobs (open-weight; OpenAI API).
3. **Stronger extraction prompts** (more context, longer prefixes, Best-of-N as in Ahmed et al. 2026). More sensitive, but open to the "manipulated prompts" objection.
4. **Copyright traps** for future content.

**Next steps**
- [ ] Top up Anthropic credit; finish La Contra M1 for Sonnet/Opus 4.5 (before 2026-11-30).
- [ ] Finish Gemini M2b and Gemini 3 Flash M1 (quota permitting); consider enabling billing on the Gemini project.
- [ ] Update the paper with sessions 3 results.
- [ ] Design the retrieval test (M4).

## 2026-11-24 — Session 4: free local experiments (no API quota)
- M5 on La Contra (Qwen2.5-7B + GPT-2-spanish reference): raw zlib AUC 0.605 (p=0.02), but the reference gives the same (0.593).
  **Calibrated: no signal** (AUC 0.45–0.54, p≥0.23). Only 41 controls, so estimates are imprecise.
- **M6 dataset inference** (`src/dataset_inference.py`; Maini et al. with calibrated features, logistic combination, 200 splits,
  Welch t-test). Results in `results/di_*.json`:
  - Random sample (695 vs 448): raw p=0.0004 (100% of splits); **reference-only p=0.007 (82%)**, so date-based controls alone
    produce false positives; calibrated p=0.02 (69%); null check (controls vs controls) p=0.53 (2%), which passes.
  - Sample-size curve (calibrated): splits with p<0.05 reach 0% at n=50, 10% at 100, 15% at 200, 20% at 300 and 45% at 448 per group.
  - La Contra: calibrated p=0.07 (44%), not significant.
- **Key design insight:** dataset inference needs a *same-period* validation set. With the Godó archive: crawled vs never-crawled
  articles (check the CC index per article), print-only content, or a two-model difference-in-differences.
- Paper updated: method families labeled (A)–(F) with an experiment→family table; dataset inference explained in plain language
  (loaded-die analogy, 4 steps, validation-set requirement); new results section with a table, the sample-size curve and validation-set designs;
  conclusions, abstract and next steps updated. Note in the premises on which providers expose probabilities.

**Next (free):** more open-weight targets (Llama 3.x, Mistral, Gemma) for M5/M6; a two-model difference-in-differences design;
matched (section/length) controls.

## 2026-11-24 — Session 5: multi-model dataset inference, placebos, matching, neighbour test
All local and free (no API quota). Scripts: `src/di_summary.py`, `src/di_placebo.py`, `src/di_matched.py`,
`src/di_robust.py`, `src/m5_neighbour.py` + `src/neighbour_analysis.py`, `src/did_llama.py`; GPU queue `src/run_queue2.sh`
(an earlier pgrep-based queue deadlocked because waiter shells matched their own pattern, so never wait on `pgrep -f <script name>`).
- **New targets** (MLX 4-bit, all 1,143 articles + La Contra): Llama-3.1-8B, Mistral-7B-v0.3, Gemma-2-9B (`results/m5_<tag>.jsonl`).
- **DI summary** (`results/di_summary.json`, GPT-2-es reference, R=100). Columns: raw / reference-only / calibrated.
  | target | unmatched | matched (440 pairs, same section, ±30% length, no live blogs) | placebo P1 |
  |---|---|---|---|
  | Qwen2.5-7B | 0.0005 / 0.007 / 0.039 | 0.0018 / 0.006 / 0.29 | 0.65 |
  | Llama-3.1-8B | 0.0009 / 0.007 / 0.027 | 0.0036 / 0.006 / 0.29 | 0.56 |
  | Mistral-7B-v0.3 | 0.0001 / 0.007 / 0.0096 | 0.0004 / 0.006 / 0.13 | 0.45 |
  | Gemma-2-9B | 0.0008 / 0.007 / 2e-5 | 0.012 / 0.006 / **0.009** | 0.33 |
- Placebos (`results/di_placebo_*.json`) clean for all models on calibrated scores (P1/P2/P3 p ≥ 0.26).
- Gemma robustness (`results/di_robust_gemma2_9b.json`): survives match tolerance 0.1–0.5 (p 0.007–0.011), single features
  (loss p=0.002, Min-K p=0.007) and dropping most sections, but **dropping "internacional" → p=0.09**. Qwen stays null (0.29–0.34).
- La Contra DI: reference-only already p=0.0095 (only 41 controls) → drift dominates; calibrated Qwen 0.07, Llama 0.010,
  Mistral 0.038, Gemma 0.23. Not interpretable.
- **Neighbour (paraphrase) test** (family B, new): score = loss(original) − mean loss(rewrites with same facts). Cancels
  both drift AND world knowledge of the events; only memorised *wording* survives. Uses the 60+60 DE-COP passages.
  Gemma: members do NOT prefer original wording more than controls (full: diff +0.048 [−0.02, 0.11]; minimal: +0.034
  [0.010, 0.057], i.e. opposite direction). ⇒ Gemma's matched-DI signal is knowledge of the period's events/topics, not
  of La Vanguardia's text.
- **Lesson:** a matched + calibrated DI result can still reflect *world knowledge* (members describe events the model
  knows from any source; controls describe events after its cutoff). A wording-specific test (neighbour gap, or
  same-period never-crawled controls) is required before claiming use of the publisher's text.
- **XGLM-2.9B reference** (`results/m5_xglm29.jsonl`; members < 2020-06 dropped): learned DI declares ALL four targets
  significant after matching (cal p 7e-4..3e-3), but XGLM-only is p≈3e-6, and calibrated Min-K% points the WRONG way
  (members less familiar than predicted) → logistic exploits negative weights; miscalibration manufactures significance.
- **Sign-constrained DI** (`src/di_fixed.py`, `results/di_fixed.json`): pre-oriented, standardised, equal-weight average,
  matched groups. Reference-only p=0.20–0.32 (clean). Calibrated GPT-2/XGLM: Qwen 0.06/0.59, Llama-3.1 0.06/0.61,
  Mistral 0.03/0.37, **Gemma-2 1e-4/0.002**. Gemma robust to reference, but neighbour test says not wording.
- Neighbour test, all models (`results/neighbour_summary.json`): null for Qwen, Llama-3.1, Mistral (p ≥ 0.15) and Gemma.
- Rule: pre-register direction and combination; conclusions must not depend on the reference model.
- **M8 Llama-3 vs Llama-3.1 difference-in-differences** (`results/did_llama.json`; 695 both / 249 Apr–Nov 2023 / 448 neither).
  Familiarity gain (3.1 over 3) larger for 3.1-only group: loss p=0.001, zlib 0.003, Min-K 0.02, Min-K++ 0.30.
  Pre-registered equal-weight combo: 3.1-only vs neither p=0.007, vs both p=0.007; both vs neither p=0.42; placebo 0.63.
  Learned DI borderline (0.06 / 0.21). Effect ≈0.17 SD (0.01 loss). Still confounded with knowledge of mid-2023 events.

**Next (free):** generate same-facts rewrites of the 249 mid-2023 articles + controls with a local instruct model and run
the neighbour test on Llama-3 vs 3.1 (separates wording from events); larger open models; with the Godó archive,
crawled vs never-crawled same-period controls.

### State at end of session 5 (2026-11-24, ~18:30 CET) — RESUME HERE
**Where we stand (one paragraph for a judge-facing summary):** no commercial model tested reproduces La Vanguardia text
(Claude 4.5/5.5, Gemini 3.x). Collection-level tests on four open-weight models (Qwen2.5, Llama-3.1, Mistral, Gemma-2)
look positive at first but are mostly time drift; after matching + pre-registered combination only Gemma-2 survives, and
the neighbour test shows it is knowledge of events, not wording. The cleanest design (Llama 3 vs 3.1, same articles) shows
the predicted pattern (p=0.007) but small and still not separated from event knowledge. Paper (`paper/paper.pdf`) is up to date
with all of this (tables tab:dimulti, tab:neigh, tab:did).

**Background runs interrupted at session exit** (both resumable: rerun the same command, they skip finished items):
- `.venv/bin/python -I src/m1_continuation.py --model gemini-3-flash-preview --n 60 --workers 1` (22/120 done, free-tier quota).
- `.venv/bin/python -I src/m2b_pairwise.py --model gemini-3.1-flash-lite --n 60 --workers 3` (352 rows; target 120×6=720).
- Anthropic credit is exhausted; Sonnet 4.5 retires 2026-11-30 (La Contra M1 for Sonnet/Opus 4.5 at 65/70).

**Next step (do first, free, local):** neighbour test inside the Llama 3 vs 3.1 design.
1. Generate 3 same-facts rewrites (full) of the first ~70-word passage for the 249 mid-2023 articles (`data/cc/mid2023.jsonl`),
   plus ~250 "both" members and ~250 controls, with a local instruct model via MLX (e.g. `mlx-community/Qwen2.5-7B-Instruct-4bit`;
   NOT Llama, to avoid self-preference). Write to `data/decop/paraphrases_mid2023.jsonl` in the same format as `paraphrases.jsonl`.
   (Expect ~10–20 s per passage: run as one sequential background script, no pgrep waits.)
2. Score originals + rewrites with Llama-3 and Llama-3.1 (`src/m5_neighbour.py`, add a `--src` argument).
3. DiD on the neighbour gap: does the 3.1-only group's ORIGINAL wording gain more than its rewrites? If yes → evidence about
   the text, not the events. Add to the paper (sec:di, after tab:did) and conclusions.

**After that:** larger open models if memory allows (16 GB RAM: ≤ ~14B at 4-bit); retrieval test (M4) design; when the Godó
archive arrives: crawled vs never-crawled same-period controls (check CC index per article), with matching + pre-registered
sign-constrained DI + neighbour test + placebos as the standard battery.
