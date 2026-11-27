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

### 2026-11-24 evening — overnight run started (~20:15 CET)
- Gemini runs stopped (stuck on free-tier quota since ~13:00). Rerun tomorrow; both resume.
- **Started `src/run_queue3.sh` → `logs/queue3.log`** (the "Next step" above, implemented):
  1. `src/local_paraphrase.py`: 3 same-facts rewrites per ~70-word passage with local Qwen2.5-7B-Instruct (MLX, temp 0.7,
     validated: no non-Latin script, length ratio 0.6–1.5, retries) for 249 NEW (Apr–Nov 2023) + 250 BOTH (<2023-03)
     + 250 NONE (controls) → `data/decop/paraphrases_mid2023.jsonl` (~15–25 s per passage, ~4–5 h).
  2. `src/m5_neighbour.py --src` scores originals + rewrites with Llama-3.1 and Llama-3.
  3. `src/did_neighbour.py` → `results/did_neighbour.json`: dgap = gap(3.1) − gap(3); prediction if trained on the TEXT:
     dgap(NEW) < dgap(BOTH), dgap(NONE). Pre-registered: loss (Mann–Whitney/Welch, one-sided) + equal-weight combination.
- **On resume:** check `tail logs/queue3.log` for "QUEUE3 done". If interrupted, rerun `./src/run_queue3.sh` (all steps resume).
  Then add the result to the paper (sec:di after tab:did; abstract/conclusions), commit and push.

## 2026-11-25 — Session 6: resume after reboot; dataset presence; retrieval test (M4)
- Queue3 had died after 2/749 rewrites (machine reboot). **Restarted `./src/run_queue3.sh`** (resumes; ~23 s/passage,
  ~5 h). Anthropic credit still exhausted (checked 07:35 UTC). Gemini free tier: 500 requests/day for
  gemini-3.1-flash-lite, resets 09:00 CET; failed calls (429) also burn quota, so probe.py no longer retries
  daily/zero-limit 429s.
- **robots.txt today (25 Nov 2026):** blocks only GPTBot, ClaudeBot, CCBot, Bytespider. No rule for Google-Extended,
  OAI-SearchBot, ChatGPT-User, PerplexityBot → answer-time retrieval is not opted out. (Added to paper premises.)
- **FineWeb-2 presence** (`src/dataset_presence.py`, URL column only via HTTP range reads; `results/dataset_presence.json`,
  hit lists `results/dataset_presence_hits_<config>.jsonl`): Catalan shards hold 5,289 and 3,323 lavanguardia.com pages
  each (~0.1% of documents). Full Catalan (5 shards) + 6/146 Spanish shards running → `logs/presence.log`.
- **M4 retrieval** (`src/m4_retrieval.py`; post-cutoff controls; tools off / Google Search / URL context × QUOTE / ASK prompts):
  - Google Search grounding: 429 on the free-tier key (needs billing). URL context works, but Google's fetcher gets
    `URL_RETRIEVAL_STATUS_ERROR` on lavanguardia.com and the model then declines.
  - Tools OFF + QUOTE: Gemini **fabricates** "the first two paragraphs" of a post-cutoff article and presents them as
    La Vanguardia's text (LCS 3 words with the real one). Relevant as misattribution, not as copying.
  - Running n=25 (off, url) then the remaining M2b pairwise → `logs/gemini_day2.log`.
- **Results (session 6, morning):**
  - FineWeb-2: Catalan (all 5 shards) 17,947 lavanguardia.com docs (17,179 URLs, crawls 2017–2024); Spanish 6/146
    shards 13,779 → est. ~330k. Our sets in scanned data (`src/presence_overlap.py`): members 37/695 (5.3% in 4.1% of
    Spanish data → consistent with ~all members present), mid2023 13/249, La Contra 12/212, controls 0. **Full Spanish
    scan running** (`logs/presence_all.log`, ~15 h, resumable; rerun `src/presence_overlap.py` after it).
  - M4 (Gemini 3.1 Flash-Lite, 25 controls, `results/m4_retrieval_*_summary.json`): URL tool fails on lavanguardia.com
    49/50 (+ homepage), works on Wikipedia, fails on elperiodico.com → site-level bot blocking. No article text reproduced
    (≥9-word matches are all the headline from the prompt). Tools OFF + QUOTE: 11 refusals, **13 fabricated "literal"
    paragraphs** attributed to La Vanguardia. Search grounding needs a billed key.
  - M2b Gemini complete: members 58.9% vs controls 65.5% (p=0.98), A-bias 78–89%. No signal.
  - Paper: premises, sec:presence, sec:m4, tab:rec + figure, abstract, limitations, conclusions updated.
- **Next:** queue3 → did_neighbour → paper (sec:di after tab:did). M4 on consumer products / search grounding needs
  billing or accounts (ask user). Anthropic top-up still needed (Sonnet 4.5 retires 2026-11-30).
- **Neighbour-DiD first run** (`results/did_neighbour.json`, tab:didneigh): dgap loss BOTH +0.012, NONE +0.013, NEW +0.001
  → predicted direction; combined p=0.069 (vs NONE), 0.065 (vs BOTH); check BOTH vs NONE p=0.53. Not significant.
  **Pre-registered replication** (`docs/prereg/did_neighbour_replication.md`, commit 92a098f before data) running:
  `src/run_queue4.sh` → `logs/queue4.log` (CC fetch of fresh mid-2023 articles → rewrites → Llama scoring →
  `results/did_neighbour_rep.json`). Resumable; on resume check for "QUEUE4 done". Report the replication alone as primary.
- Gemini 3 Flash M1: 47/60 members (quota). Median LCS 3, max 13 = quoted Biden statement (syndicated), not LV wording. Controls pending (rerun same command next day).
- **NYT-method literature** (user question): Freeman et al. 2024 (arXiv 2412.06370) and Su et al. 2024 (arXiv 2409.12367)
  added to `docs/literature_review.md` and the paper (sec. methods (A), refs freeman2024, su2024). Implemented Su et al.'s
  sentence-level decomposition as **M9** (`src/m9_decomposition.py`, plain prompt, no role-play; sentences with quotation
  marks flagged as possibly syndicated, ~21% of sentences). Scheduled `src/run_gemini_day3.sh` → `logs/gemini_day3.log`:
  waits for 2026-11-26 09:01, runs M9 on gemini-3.1-flash-lite (60+60 × 4 sentences), then resumes Gemini 3 Flash M1.
- **User decisions (2026-11-25 afternoon):** run role-play prompts (as a labelled upper bound), and use our open models
  instead of paid APIs.
  - `probe.py`: multi-turn messages for all providers; **local MLX provider** (`ask_local`, greedy, logs weights commit
    hash as `model_reported`); `raw=True` = plain completion for base models.
  - `m9_decomposition.py`: `--style plain|roleplay|completion`, `--context prev|prefix`. Role-play = Freeman et al.'s
    "2079 student" prompt adapted to La Vanguardia (Jordi, Barcelona) + fake assistant acknowledgement.
  - Downloaded mlx-community/Meta-Llama-3.1-8B-Instruct-4bit (disk: ~6 GB free left; don't download more without cleaning).
  - **Queue5** (`src/run_queue5.sh` → `logs/queue5.log`, resumable): base Llama-3.1/Gemma-2/Qwen2.5/Mistral completion with
    prefix on La Contra (212+41) and random (150+150), k=5; then Llama-3.1-Instruct and Qwen2.5-Instruct, plain + role-play.
    Runs alongside queue4 (shared GPU, ~8 s/query).
  - Replication note: only 168 fresh mid-2023 articles were found (417 − 249), so NEW2 ≈ 168.
  - TODO: role-play M9 on Gemini on a later free-tier day (day3 quota goes to plain M9).

### State at end of session 6 (2026-11-25, ~18:00 CET) — ALL JOBS STOPPED (user request: too slow)
No background jobs, no schedulers (run_gemini_day3.sh removed; no crontab). Final numbers are in the paper.
- **FineWeb-2** stopped at 78/146 Spanish shards (53%) + all Catalan: Spanish 164,568 LV docs (est. ~280k, 0.06%);
  Catalan 17,947 (0.10%). Overlap: members 292/695 (42% at 53% → ~80% projected), mid2023 69/249, La Contra 67/212,
  controls 0/489. Hits concentrated in crawls 2019–2023 (81%), pub years 2017–2021. Resume: rerun
  `src/dataset_presence.py --config spa_Latn --shards 999` (resumable), then `src/presence_overlap.py`.
- **M9 local** (Llama-3.1-8B base, completion + prefix): La Contra 100 members (460 sents) max LCS 4, 41 controls (164)
  max 5, median 1; random 31 members (123) max 7. No exact sentence. Instruct / role-play / other models NOT run.
- **Neighbour-DiD replication**: stopped at 247/~811 rewrites (`data/decop/paraphrases_mid2023_rep.jsonl`), no scoring.
  Resume with `./src/run_queue4.sh` (resumable; CC fetch step will just re-check). Only 168 fresh NEW2 articles.
- Paper: new sec:m9, sec:status (tab:status: missing items + costs/problems), conclusions on most suspicious models
  (Gemma-2 > Llama-3.1 > Mistral/Qwen; closed models plausible but untested at power) and most exposed content
  (crawled 2019–2023 / published 2017–2021; Catalan edition proportionally most exposed; not post-2024, post-opt-out,
  paywalled/print-only; quotes are not evidence).
- **Highest-value next step:** finish the pre-registered Llama 3 vs 3.1 replication (≈1 day local, or hours on a rented GPU).

## 2026-11-26 — Session 7: M10 "LV-only knowledge" screening (cheap triage before regurgitation tests)
**Idea (user):** before costly M1/M9 runs, flag candidate models by asking for information that exists (almost)
only on lavanguardia.com. Not evidence on its own (facts ≠ wording; copies exist); it is a filter.
- Checked user's examples: horóscopo is in CC but generic/partner content (`-ctx`), games not crawled/third-party,
  Premios Godó widely reported elsewhere, hemeroteca only as scanned-page thumbnails → all discarded.
- `src/m10_exclusive_facts.py` (build / run / summary), queue `src/run_m10_local.sh`, log `evidence/m10_exclusive/`.
  Items built deterministically from data/cc (`data/m10/items.jsonl`, sha256 printed by build): **url_id** (complete the
  URL: numeric ID), **byline** (author; title-leaks and generic bylines dropped; full name required), **box_title**
  (La Contra intro-box heading), **cloze** (La Contra intro / "según ha podido saber LV" sentences, whole name spans masked).
  Members ≤2023, controls ≥2025-09. Chat models asked for a best guess (`--abstain` optional); base models get a
  plain page to continue. Summary re-scores from raw outputs. n=60 per stratum (442 items/model, ~15 min local).
- **Results** (`results/m10_summary.json`): exact answers ≈ nothing for every model: url_id 0 exact, box_title 0,
  byline ≤3/60 (Gemini, = control rate), cloze member ≈ control (guessable from context: PSOE, Greenpeace…).
- **Key finding — URL-ID-as-date:** LV IDs are a counter (~3,000/day). Converting the predicted ID back to a date
  (interpolation over real corpus IDs): **Gemini 3.1 Flash-Lite median error 3 days on 2021–2023 members (16/49 within
  1 day, 30/49 within 7 days) vs 0/60 controls within 7 days (p=3e-14)**; e.g. 2023-02-09 true 8746377 → 8746375.
  Gemma-2-9B base: median 162 days (rough); Llama-3.1 base 914; Qwen/Llama instruct: nonsense. → Gemini flagged as
  having dense exposure to lavanguardia.com URLs of 2021–2023 (only from LV URLs: its own pages in crawls, or
  links/citations to them, e.g. Wikipedia references — confound to check). Not article-specific memorization.
- Gemini free-tier quota: 500 req/day for flash-lite; first attempt hit 429 (quota already used); resume retries errors.
**Next**
- [ ] url_id test is ~1 short query/article: run it on all reachable API models (Claude, other Gemini versions, OpenRouter).
- [ ] Same-period control for url_id: another outlet's counter-style IDs (e.g. other Spanish newspapers) → is the
      skill LV-specific or a generic "news URL" skill? Also split members by whether the URL is cited on Wikipedia.
- [ ] Use url_id-date error per model as the triage score; run M1/M9 at power only on flagged models (Gemini first).

## 2026-11-26 — Session 7b: M10 extensions, then STOP + paper simplification
**Done**
- URL-number test on all Gemini-API models (`src/run_m10_api.sh`): 3.5 Flash-Lite median 2 days (31/49 vs 0/60,
  p=7e-15), 3 Flash 4 days (8/13 vs 0/9; quota). 2.5 models closed (404), 3.1 Pro no free tier, 3.5–3.8 Flash 20 req/day,
  Gemma-4 (thinking) returns empty answers → stopped. Fixed `probe.ask` routing of `gemma-*` to the Gemini API.
- **Is the URL number learnable externally? Yes.** Simulation: 5 anchor URLs over 2021–23 → 3.7-day error, 20 → 1 day.
  `src/m10_url_mentions.py`: one FineWeb-2 Spanish file has 136 written-out LV article URLs, all on third-party pages,
  none in LV's own pages (links are stripped) → ~20k in Spanish FineWeb-2. The signal = exposure to LV URLs only.
- Outlet control (`src/m10_outlet_ids.py`, El Periódico/El Confidencial/El Español): stopped (CC index too slow);
  28 EP titles + 2,693 EP (date, ID) pairs collected in `data/m10/`.
- **La Contra Q→A recall** (`build-qa`; 202 members, 76 controls incl. new `data/cc/lacontra_controls_more.jsonl`):
  Gemini 3.5 Flash-Lite 15/202 vs 5/76 (no signal, hits guessable); Gemma-2 base 2/151 vs 0/51 (stopped at 202/278). Other local models cancelled.
- Methodological rule added to CLAUDE.md: copies of LV text count as LV content; the confound is independent information.
- Collection-fingerprint test (La Contra format, LV house style: "en el 20xx" 42%, Catalunya 98%) designed, not implemented.
- **Paper simplified** (7 pages, premises + summaries, one overview table, "Evidence found so far", "Promising
  avenues and where to spend"). Full detailed version moved to `docs/technical_report/technical_report.tex` (+ M10
  additions). Per-experiment status, reasons, implications, worth-finishing: `docs/experiment_status.md`.

### State: ALL JOBS STOPPED (user decision: no more spending, no quota waits)
Recommended next steps if work resumes (see docs/experiment_status.md): (1) collection test with the archive and
same-period never-crawled controls, incl. large open models on a rented GPU; (2) finish the pre-registered Llama
replication (`./src/run_queue4.sh`, resumable); (3) retrieval tests on consumer assistants with a counsel protocol;
(4) copyright traps.

- Paper: new section "What the negative results do and do not show" (nulls count against memorization/GEMA route, not
  against training; missing positive control). New first-priority avenue: positive control on OLMo (published training
  data, infini-gram counts), free. Added to docs/experiment_status.md and CLAUDE.md rules. Not run.

## 2026-11-26 — Session 7c: positive control, collection-level model list, Colab handoff
- **Positive control.** OLMo 2: training mix is English-filtered (infini-gram: 0/42 LV articles) → discarded.
  **Apertus-8B base** (Swiss AI; FineWeb-2; robots opt-outs as of Jan 2025; Goldfish loss): probabilities on all
  articles + La Contra Q→A. Same-period in-FW2 vs not-found: nothing (diluted, scan 53%). In-FW2 vs post-cutoff,
  calibrated: loss AUC 0.560 (p=0.003), zlib 0.562 — same size as Llama/Qwen/Mistral (0.54), below Gemma-2 (0.59).
  Q→A: 0/63 facts for interviews in its data. ⇒ Nulls say nothing about training; faint traces = what training looks
  like. `results/positive_control_apertus.json`; paper section "What the negative results do and do not show".
- Paper: new section "Which models can be tested at collection level, and until when" (open weights incl. BSC
  Salamandra/ALIA; OpenAI prompt-logprob models shut 2026-09-28; Claude Sonnet 4.5 retires 2026-11-30; litigation hold).
- BSC: open weights (Apache 2.0), 20 CC snapshots + CATalog (CC-based); LV not named as a source. No lawsuit against
  BSC found (only Jot Down 2025 criticism over Dialnet, CEDRO complaints) — waiting for the user's source.
- Colab: `probe.ask_hf` (model id `hf:<repo>`), `m5_hf.py` on CUDA/bf16, requirements skip mlx on Linux.
  Handoff: `docs/colab_handoff.md` (data/ must be copied via Drive; repo is PUBLIC).
- Off-repo files (data, evidence backup, logs, FineWeb-2 hit lists, MANIFEST with SHA-256) uploaded by the user to Google Drive (ruben.tous.2@gmail.com) lavanguardia_work/data/. Colab instructions in docs/colab_handoff.md.

## 2026-11-26 — Session 8: resume on Google Colab (T4)
- Data from Drive (`lavanguardia_work/data/`) verified against MANIFEST (3 zips OK) and unzipped. FineWeb-2 scan resume
  state consistent (78/146 Spanish shards done, no orphan hits).
- **Colab volatility:** `src/colab_sync.sh` mirrors the whole working tree to `MyDrive/lavanguardia_work/colab_state/`
  every 5 min (rsync, atomic per file, no deletes). Resume procedure at top of `docs/colab_handoff.md`.
- **GPU is a T4 (15 GB, no native bf16)**: new `src/hf_load.py` (precision auto|bf16|fp16|int8|int4, recorded in every
  row with the weights commit); `m5_hf.py` (`--precision`) and `probe.ask_hf` (env `HF_PRECISION`) use it.
  ALIA-40b / 70B models do not fit a T4 → need an A100 runtime or rented GPU.
- Running (sequential, resumable): `src/run_colab_fw2.sh` (finish FW2 Spanish scan → presence_overlap →
  positive_control_apertus; log `logs/colab_fw2.log`; network-only) and `src/run_colab_salamandra.sh`
  (Salamandra-7B base int8: m5 random + La Contra, m10 qa + url_id n=300; log `logs/colab_salamandra.log`).
  Only one GPU job; the scan uses no GPU.
**Next**
- [ ] When the scan finishes: re-read `results/positive_control_apertus.json` (same-period in/out split now clean).
- [ ] Analyse Salamandra: calibrate with GPT-2-es as in M5/M6, compare with Apertus positive control; url_id date error.
- [ ] Remove the redundant Drive copy loop from `run_colab_fw2.sh` once it has finished (colab_sync.sh covers it).
- [ ] Decide on an A100 runtime for ALIA-40b.
- **Ported to transformers** (CPU smoke-tested): `local_paraphrase.py` (`--model hf:<repo>`, 3 rewrites per round,
  per-article torch seed, backend/precision/commit per row) and `m5_neighbour.py` (`--model hf:<repo>`, same scoring
  function as MLX). Queue: `src/run_colab_queue4.sh` (nf4 4-bit; rewrites to a NEW file `paraphrases_mid2023_rep_hf.jsonl`,
  NEW2 frozen at 168). **Deviation note drafted in `docs/prereg/did_neighbour_replication.md`, awaiting user approval;
  commit it before any scoring.** Needs HF_TOKEN (Llama licences) in Colab Secrets.
- Paper: new section "Training datasets and models at a glance" (tab:datasets, tab:models). Salamandra row is
  preliminary (quick calibrated AUC 0.571, all members vs controls; Apertus same measure 0.567); update when its m10 ends.
  Colab TeX: texlive + cm-super (vector fonts).

### Session 8, evening: FineWeb-2 scan finished; positive control re-run
- Spanish FineWeb-2 fully scanned (146/146): 310,502 LV docs (0.07%), 303,226 distinct URLs; crawls 2019–23 = 85%,
  pub years 2017–21 = 61%. Overlap: members 567/695 (82%), mid2023 204/249, La Contra 95/212, controls 0/489.
- Positive control re-run (`results/positive_control_apertus.json`): Apertus in-FW2 vs post-cutoff calibrated loss AUC
  0.550 (p=0.003); Q→A 0/90 in-data, 1/76 controls. Salamandra (same split) 0.564, Gemma-2 0.582, Llama-3.1 0.539,
  Mistral 0.536, Qwen2.5 0.527.
- **Same-period in vs not-found is reversed on every model (AUC ≈0.40), including the 2018 reference**, and stays so
  within year+section (`src/presence_selection_check.py` → reference 0.42; Apertus calibrated 0.44 p=0.01). FineWeb-2's
  selection picks different text; "not found" ≠ "unseen". Rule added to CLAUDE.md. Paper (data, positive control,
  avenues, tables) and technical report updated.
- Llama replication rewrites running (~600/811 at 17:30 UTC); Salamandra Q→A paused at 610/878, resumes after.
- Paper: new section "Finding 1: the articles are in the public sources of AI training data" (tab:presence,
  tab:overlap, fig:presence from `src/presence_by_year.py` + `paper/make_fig_presence.py`); datasets table moved there;
  glance section now "Models at a glance".
**State when the user left (~18:00 UTC):** replication rewrites ~80% (resumable), then scoring + DiD; Salamandra Q→A
610/878 paused (resumable). Resume: one Colab cell in `docs/colab_handoff.md` ("Quick resume") → `src/run_colab_resume.sh`.
**Next after resume:** write up the replication (primary test as pre-registered, report the 1 skipped article
8191781), finish Salamandra (Q→A facts in/notfound/control, URL-number date error vs Apertus/Gemini), update the
Salamandra row in tab:models, commit + push. Copy new `evidence/` lines from Drive to the Mac master log (append only).

## 2026-11-26 — Session 9: Colab resume (evening)
- Restored the Drive mirror (last sync 18:58 UTC); only diffs were lost exec bits (`chmod +x src/*.sh`). Checked every
  pending step against its output before resuming: rewrites 808/811 and Llama-3.1 scores 808/808 were reused; Llama-3
  scoring resumed at 534/808; Salamandra probabilities were already complete (1143 + 253 rows).
- `src/m5_hf.py` now checks for finished rows **before** loading the model, so a resume no longer loads Salamandra
  just to skip complete steps. (`m5_neighbour.py` and `local_paraphrase.py` still load first: a few minutes wasted per resume.)
- **Pre-registered Llama 3 vs 3.1 neighbour replication: DONE, NOT CONFIRMED** (`results/did_neighbour_rep.json`).
  n NEW2/BOTH2/NONE2 = 168/442/198. NEW2 vs NONE2 combined +0.122 SD p=0.097; NEW2 vs BOTH2 +0.118 SD p=0.067;
  check BOTH2 vs NONE2 −0.012 p=0.57 (clean). Loss MW p=0.053 / 0.12. Same direction and size as run 1 (p≈0.07).
  **Correction:** 3 passages were dropped (no 3 valid rewrites: 7740491, 8098952, 8191781), not 1 as noted before;
  the drop is deterministic (per-article seed), so reruns don't change it.
  Secondary pooled (both runs, mixed backends; `results/did_neighbour_pooled_secondary.json`): NEW vs NONE p=0.038,
  NEW vs BOTH p=0.11, but check BOTH vs NONE not clean on loss (MW p=0.039) → adds nothing reliable.
  Paper, technical report and docs/experiment_status.md updated. Reading: a consistent ~0.1 SD hint about Llama-3.1;
  settling it needs thousands of same-period never-online articles (publisher's archive), not more crawled ones.
- Salamandra m10 (Q→A + URL number) resumed from 610/878 (`logs/colab_salamandra.log`).
- **Salamandra-7B finished (RESUME done 21:40 UTC).** Q→A La Contra (`results/positive_control_apertus.json`,
  key `qa_lacontra_salamandra7b`): facts 2/90 in-FW2, 3/112 not found, 2/76 controls, max LCS 4 → no content recall
  (as Apertus 0/90). **URL number as date** (`results/m10_summary.json`, n=300/set): member median error 65 days
  (2021 74, 2022 63, 2023 64), 12/245 within 7 d vs 0/300 controls (p=5.9e-5); Gemini 2–3 d, Gemma-2 162, Llama-3.1 914.
  = rough exposure to LV URLs (third-party links in CC suffice), not memorization. Paper (overview table, M10 text,
  tab:models row), technical report, experiment_status updated; PDFs rebuilt.
- `positive_control_apertus.py`: also splits Salamandra Q→A; fixed stale `fw2_spanish_scanned_fraction` (0.534 → 1.0).
- Removed the stale local `.last_sync_utc` restored from Drive (it overwrote Drive's stamp on each sync; cosmetic).
### State: ALL COLAB JOBS DONE (no queue running except the Drive mirror loop)
**Next**
- [ ] Copy new `evidence/` lines from Drive (`colab_state/lavanguardia/evidence/`) to the Mac master log (append only).
- [ ] Remaining avenues (docs/experiment_status.md): collection test with the publisher's never-online archive;
      ALIA-40b needs an A100 or rented GPU; retrieval tests on consumer assistants with a counsel protocol; copyright traps.
- Paper, Legal context: new paragraph "Can the newspaper claim for training done before its opt-out?" (not
  retroactive; remaining routes: post-opt-out training on old copies / Art. 4(2) retention, GEMA memorization, unlawful
  copies + answer-time use; evidential consequence: post-17-Mar-2026 wording knowledge would date the copying).
- Paper, Legal context: added Like Company v. Google (CJEU C-250/25, AG opinion 3 Nov 2026: TDM covers training in
  principle; model stores no copy, contra GEMA; regurgitated outputs can be reproductions; answer-time reuse test) and a
  paragraph "Training and memorization are different legal situations". Also in docs/literature_review.md.

## 2026-11-26 — Session 9b: M11 NYT-style extraction (adversarial upper bound), pre-registered
- User question: did we try the NYT-case tricks? Answer: no. M1/M9 were neutral, one attempt each; role-play code
  existed but was never run (credit/time). Rule was "label and report separately", not "exclude".
- **Pre-registered** `docs/prereg/m11_nyt_style.md` (commit 6e3be81, before any member query): Freeman et al. role-play +
  fake assistant turn, 110-word opening, best-of-10 (1 greedy + 9 samples T=0.8 top_p=0.95, seed = article ID), same for
  controls. Sets: La Contra 60+60, random 40+40. Models in order: Salamandra-7B-Instruct, Llama-3.1-8B-Instruct,
  Qwen2.5-7B-Instruct (nf4 on T4, ~84 s/article ≈ 4.7 h/model). Primary: best LCS outside quotes, MW one-sided,
  α=0.05/3. `probe.ask_hf_samples` logs all 10 attempts in one evidence record (`evidence/m11_nyt_style/`).
- Pilot: 1 control article on Qwen (timing), `evidence/m11_pilot/`, not analysed.
- Running: `src/run_colab_m11.sh` → `logs/colab_m11.log` (resumable; rerun after a disconnect, HF_TOKEN needed).
**Next:** when "M11 done" appears: `python -I src/m11_nyt_style.py summary` (already run at the end), inspect every member
run ≥15 words side by side and check for copies elsewhere, write up as a labelled upper bound in the paper.
- Paper, Legal context: paragraph on what proof of pre-opt-out training is worth without regurgitation.
- Discussed (no code): how to run M11 on Gemini — needs GEMINI_API_KEY (Colab Secrets), sampling params + seed in
  `probe.ask_gemini` (fixed at temperature 0 now), one API call per attempt, count `RECITATION` stops per set, and a
  dated prereg amendment before the first query. Free tier ≈ 4 days (2,000 requests); paid ≈ a few dollars.

### State at end of session 9 (2026-11-26, 22:30 UTC) — ALL JOBS STOPPED (user request)
- No queue, no Python job, no sync loop running. Final Drive sync done after this entry (see below).
- **M11**: stopped at 7/200 articles on Salamandra-7B-Instruct (La Contra members only; best LCS ≤3 words). No controls
  yet → no result; not reported as one. Resume: `./src/run_colab_m11.sh` (skips finished articles; ~14 h for 3 models).
- Everything else of this session is finished, committed and in the paper: replication (not confirmed), Salamandra
  (no recall, rough URL-number knowledge), legal context (pre-opt-out training, training vs memorization, Like Company AG).
**Next, in order of value** (see docs/experiment_status.md and the paper's "Promising avenues"):
1. Finish M11 on the open models (free, ~14 h Colab), then optionally Gemini (key + prereg amendment).
2. Copies-vs-trace test (does the collection trace grow with the number of crawl copies of each article?), CPU only.
3. Literature: add Duan 2024, Kandpal 2022, Wei 2024, Puerto 2024, Jagielski 2023 to docs/literature_review.md;
   Goldfish-loss caveat on the Apertus positive control in the paper (offered, not done).
4. Needs money or the publisher: never-online archive collection test, ALIA-40b/70B on a rented GPU, retrieval tests
   with a counsel protocol, copyright traps.
5. Copy new `evidence/` lines from Drive to the Mac master log (append only).
- Rotate the HF and GitHub tokens (they were pasted in chat); use Colab Secrets next time.

## 2026-11-27 — Session 10: resume M11 on Colab (T4)
- Restored the Drive mirror (same commit 092374a; only exec bits differed). 7/200 Salamandra rows + 7 evidence records intact.
- 09:23 UTC: restarted `src/colab_sync.sh loop 300` and `src/run_colab_m11.sh` (→ `logs/colab_m11.log`). Article 8 done at
  ~09:30. Expected: Salamandra done ~14:00 UTC, then Llama-3.1-8B-Instruct (gated: needs a HF token, via
  `hf auth login` or HF_TOKEN in the env) and Qwen2.5-7B-Instruct, ~4.7 h each.
- Not expected to finish this session. Resume: restore mirror, `chmod +x src/*.sh`, restart the sync loop, rerun
  `./src/run_colab_m11.sh` (skips finished articles).
- **M12 reverse URL test** (user idea: ID → title). Pre-registered `docs/prereg/m12_url_reverse.md` (7101c47), amended
  before any member-pair query (a62685d: v1 prompt was read as "visit the URL" → from-memory wording v2).
  117 member + 96 control pairs (same date + section); pair score = overlap(own title) − overlap(partner's title), 0 by
  construction if only date/section is used. Running on gemini-3.5-flash-lite (`logs/m12_gemini-3.5-flash-lite.log`,
  resumable; key passed as env var only, never written to disk). Then replicate on gemini-3.1-flash-lite.
  Controls answer "no information" (expected); members get date-topical guesses.
- **Exploratory: M10 errors in IDs, not days** (`src/m10_id_error.py` → `results/m10_id_error.json`). Benchmark = a
  "date oracle" that knows the exact publication date and guesses midday's ID (leave-one-out interpolation over our
  corpus). Gemini 3.5 Flash-Lite median error 1,325 IDs vs oracle 1,281 (3.1 FL 1,638; 3 Flash 1,013 vs 1,215): Gemini
  knows LV's counter about as precisely as ~1,500 dated LV URLs would teach. Salamandra 127k, open models far worse.
  Within ±200 IDs: 7/49 (oracle midpoint 2/49, but a guess uniform within the right day gives ~4–10 → no excess).
  Near-exact hits: 8746377→8746375 (Burt Bacharach obituary, 3.1 FL) and 8931138→8931141 (Isabel Garcia Pagan column,
  3 Flash): chance ≈ 7/2,262 per query if the day is known → expected ~0.3 over ~110 Gemini member answers, observed 2
  (P ≈ 4%). Suggestive, not conclusive; check whether those two URLs are linked on third-party pages.
- **M12 result (gemini-3.5-flash-lite): NULL** (`results/m12_url_reverse_summary.json`). 117 member pairs: mean pair
  score +0.006, 10 positive / 7 negative / 100 zero, Wilcoxon p=0.053 (not significant); 95 control pairs: −0.0007,
  p=0.67; members vs controls MW p=0.25; overlap ≥0.8: 0 members, 0 controls. 46/234 member answers refused. Partial
  matches are date-topical (daily "Precio de la luz", Severodonetsk, PSOE–Junts). Pilot control pair 09155a565d23
  excluded from analysis (`PILOT_PAIRS`), as amendment 1 says. Gemini knows the counter, not which article has which ID.
- Web search for the two near-exact IDs (8746377, 8931138): no third-party page found (weak check).
- Replication on gemini-3.1-flash-lite launched (`logs/m12_gemini-3.1-flash-lite.log`, ~1 h).
- Paper updated (user request: report suspicious findings even without proof): overview row, "Why we still find it
  suspicious" / "What argues against it" in Details paragraph, Evidence item 4, models table, new avenue "Settle the
  article-number question", Conclusions. docs/experiment_status.md rows added.
- Note: waited on M12 with `pgrep -f` in a background shell → matched itself (the CLAUDE.md trap). Use `ps | grep '[p]ython'`.
- User leaving (~10:45 UTC): pushed everything to GitHub (origin was at 092374a: sessions 9–10 had not been pushed).
  Started `src/autosave.sh 600` (commit M11/M12 results + push + Drive sync every 10 min). Running unattended: M11
  (Salamandra → Llama needs HF login → Qwen), M12 replication on gemini-3.1-flash-lite.
  **Pending for next session:** add the M12 replication result to the paper; rebuild paper PDF (no LaTeX on this runtime);
  rotate the HF, GitHub and Gemini keys (pasted in chat).

## 2026-11-27 — Session 11: fix Drive/GitHub inconsistency (fresh Colab runtime, T4)
- Fresh runtime; repo cloned from GitHub (d204e0c, last autosave 11:27 UTC). The previous VM died after 11:33 UTC.
- **Found: the Drive mirror was stale and shorter than GitHub**: line-complete prefixes of each file (M11 22/117 rows,
  M12 3.5-FL 38/428, M12 3.1-FL missing), `.git` broken ("bad object HEAD"), `data/m12/` empty. Drive uploads
  asynchronously and was ~1.5 h behind when the VM died. Restoring Drive over the clone (old handoff) would have lost rows.
- **Fixed:** restored `data/`, `evidence/`, `logs/` from Drive + the 26-Nov zips (all hashes OK vs MANIFEST); rebuilt
  `data/m12/pairs.jsonl` (sha256 matches the prereg); rebuilt the Drive mirror from the verified tree (`.git` included).
  New `src/colab_sync.sh restore` (untracked folders only, never overwrites with older/shorter files, flags stale
  Drive copies); handoff doc rewritten (GitHub first; `drive.flush_and_unmount()` before leaving).
- **Chain-of-custody gap (not repairable):** raw evidence records lost for 95 M11 rows and 816 M12 rows
  (all of the 3.1-FL replication). Result rows are intact in git. Documented in `docs/evidence_gaps.md`; new
  `src/evidence_audit.py` → `results/evidence_audit.json`. Not reconstructed from result rows.
- Note: github.com/rtous/lavanguardia is **public**; results rows include article text and model outputs.
**Next**
- [ ] Decide: re-run the 911 queries without raw records (M12 ≈ 2 h API at flash-lite cost; M11 ≈ 2.2 h GPU) or report with the gap note.
- [ ] Resume M11 (Salamandra 117/200, then Llama-3.1, Qwen2.5); analyse M12 3.1-FL replication; rebuild paper PDF.
- [ ] Off-Drive copy of `evidence/` (e.g. private GitHub/HF repo) so a VM loss can't drop raw records again.
- **Chain-of-custody re-run started (17:06 UTC)**, as amended before any query (`docs/prereg/amendment_rerun_custody_20261127.md`,
  cc78b71): `src/run_colab_rerun_custody.sh api|gpu` → `results/rerun_custody/`, raw records in `evidence/*_rerun/`.
  `compare` subcommands in both scripts → `results/rerun_custody/m1{1,2}_compare.json`.
  - M11 Salamandra (117 articles, ~2.7 h): first article **identical to run 1** (all 10 attempts, same weights commit).
  - M12 gemini-3.5-flash-lite: 61/426, then **free-tier daily quota (429)**; rerun `api` after the reset (08:00 UTC)
    or with billing. Answers are not identical to run 1 (0/61 same text; same substance, e.g. "fecha futura"
    refusals on controls): Gemini is not deterministic at temperature 0. Compare statistics, not texts.
  - M12 gemini-3.1-flash-lite: running (~7 queries/min).
  - Running alongside: `colab_sync.sh loop 300`, `autosave.sh 600` (now also commits `results/rerun_custody/`).
- Paper (user request): made explicit that the collection-level test cannot be run on ChatGPT/Claude/Gemini via public APIs
  (needs word probabilities): abstract, method (D), avenues (new "Limitation" + open relatives = circumstantial), conclusions.
  PDF rebuilt (texlive installed on this runtime).
- Paper (user request): new Section 1.1 "The questions, and what can answer each" (7 questions: crawling/when/who,
  datasets, documented vs probable models, training + when, memorization, answer-time use, future proof), each with
  evidence route and status. New open items: request server logs; check AI Act training-content summaries; scan CATalog.
- M12 replication on gemini-3.1-flash-lite (run 1, 426 queries): **NULL, replicates 3.5-FL**: pair score +0.004,
  p=0.26; vs controls p=0.50; 0 answers ≥0.8 overlap. `results/m12_url_reverse_summary.json` now has both models.
- Docs/paper update: paper (tab row "replicated", M12 replication sentence, chain-of-custody gap bullet), technical
  report (new M12 subsection + table, evidence-gap paragraph, next steps), experiment_status (M11/M12 rows + new
  items: custody re-run, server logs, AI Act summaries, CATalog), colab_handoff (current running state). PDFs rebuilt.
- Running at ~18:00 UTC: M11 custody re-run (GPU, ~2 min/article, 11/117), sync loop, autosave. M12 re-run waits for quota.
- **AI Act training summaries checked** (`docs/ai_act_summaries.md`; PDFs + robots.txt with SHA-256 in
  `data/ai_act_summaries/`, gitignored): 12 summaries read. None names LV or any specific domain. OpenAI GPT-5.2/5.5/
  6 Astra, Mistral Large 3, DeepSeek-V4 declare **Common Crawl** text (documentary link with our CC measurement).
  GPT-6 Astra collection to May 2026, Grok Jan 2024–Jun 2026, Muse Spark to Jun 2026. LV robots.txt never names
  xAI/Meta crawlers nor Google-Extended; no TDMRep/TDM headers → no machine-readable reservation for them even now.
  Anthropic summaries exist on trust portal but not retrievable here. Gemini 3 Pro and Gemma 4 summaries identical.
- Paper (user request): open-weight relatives → commercial transfer levels (high: Llama 3/3.1 → Meta AI 2024–25;
  moderate: Gemma ↔ Gemini, gpt-oss ↔ GPT; low: Mistral-7B, Qwen2.5; none otherwise), stated per suspicious model in
  the Evidence section + models table; new evidence item "developers' own declarations"; AI Act paragraph in
  Finding 1; opt-out bullet; Q3 status. Technical report: AI Act paragraph. PDFs rebuilt.
- Paper (user request): Conclusions now open with Table "Per-model summary" (tab:verdicts): one row per model (15),
  columns: our test results / trained on data containing LV (documented or AI-Act declared) / relative of a suspicious
  model (transfer level) / overall. PDF rebuilt (16 pages).
- **Fixed another restore inconsistency:** local `results/dataset_presence_hits_spa_Latn.jsonl` (from the 26-Nov extras
  zip) had only 164,568 of 310,502 hits (zip made before the scan finished). Replaced with the Drive copy (310,502 docs,
  303,226 URLs, 146 shards: matches the paper). Both hit lists are gitignored; Drive is their only full copy.
- **Most-copied articles (running):** `src/fw2_cluster_sizes.py` reads FineWeb-2's `minhash_cluster_size` (number of
  near-duplicate documents across all CC dumps 2013–2024, same page recrawled + copies on other sites) for every LV
  document → `data/fw2_cluster_sizes/` → `top` → `results/fw2_most_copied.json`. Log: `logs/fw2_cluster_spa.log`.
- Per-article outliers (`src/outlier_articles.py` → `results/outlier_articles.json`): **none stands out**: best member
  vs best control M1 13/11 words, M9 5/5, M11 10/8; cloze multi-model hits 16/71 members vs 10/33 controls; Q→A double
  hits guessable (PSOE, Tierra, Nuevo Testamento). Near-exact URL numbers (8746377, 8931138) NOT repeated by sibling
  Gemini models (3.5-FL off by 158 and 1,198; 3.1-FL off by 1,421 on the second) → likely luck.
- FineWeb-2 copy-count scan: per-row-group reads hit HF 429 rate limits; switched to whole-shard downloads (~55 s/shard,
  `/content/fw2_tmp`, outside the repo so the Drive sync never sees it). Catalan done; Spanish 30/146 at 19:00 UTC.
  Full hit lists backed up gzipped to `MyDrive/lavanguardia_work/data/hits_*.jsonl.gz` (SHA-256 in MANIFEST.txt).
- Paper: new avenue "Aim extraction tests at the most-copied articles" (+ control design caveat: FW2 ends 2024).
- Lesson: `ps | grep [p]attern | xargs kill` inside a shell whose own command line contains the pattern kills that
  shell (exit 144). Kill in a separate command.
### State at end of session 11 (2026-11-27 ~19:05 UTC) — see `docs/colab_handoff.md` table for exact resume commands
- Running: M11 custody re-run (83/117, identical to run 1), FineWeb-2 copy-count scan (Spanish 30/146), sync loop, autosave.
- Waiting: M12 custody re-run (Gemini free quota; resume after 08:00 UTC), then M11 run 1 (117/200 Salamandra → Llama → Qwen).
**Next, in order:** (1) finish/resume the jobs above; (2) compare runs → paper + evidence_gaps.md; (3) top-20 most-copied
list → pre-registered extraction test; (4) server logs request to the publisher; retrieve Anthropic's AI Act summaries;
scan CATalog; (5) rotate HF, GitHub and Gemini keys (pasted in chat again this session).
- Paper (user request): new unnumbered section "In short" after Conclusions (two plain paragraphs for management). Corrected from the user's draft: CC = "every capture we checked" (no total count); Gemini is not "based on Gemma" (Gemma is its smaller open sibling); declared CC = "probable", not certain; "page numbers" = article numbers in URLs; legality = probably lawful before opt-out, with open questions listed.
