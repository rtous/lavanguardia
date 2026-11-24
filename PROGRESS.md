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
