# Experiment status (as of 2026-11-26, all jobs stopped)

Exploratory phase: the aim is to find viable avenues, not to finish every experiment. For each experiment: what was
done, why it is incomplete (if it is), what that implies, and whether finishing it is worth it.
Full methods and statistics: `docs/technical_report/technical_report.pdf`. Session history: `PROGRESS.md`.

Legend for "worth finishing": **Yes** (cheap and informative), **Only if** (conditional), **No** (low expected value).

## Provenance

| Experiment | State | Why incomplete | Implication | Worth finishing? |
|---|---|---|---|---|
| Common Crawl presence (`src/cc_fetch.py`) | Done | — | Full LV text is in every crawl 2019–Mar 2026 | — |
| robots.txt history (`src/robots_history.py`) | Done | — | AI opt-out of news only from 2026-03-17 | — |
| FineWeb-2 presence (`src/dataset_presence.py`) | Catalan 100%, Spanish 53% | Stopped for time (~8 h of downloading left) | ~80% of our members projected to be in FineWeb-2 | **Yes, now** (free, Colab): gives clean same-period in/out groups for the positive control and for any FineWeb-2-trained model |
| LV URL mentions in FineWeb-2 (`src/m10_url_mentions.py`) | 1 of 146 Spanish files | Enough for an estimate | ~20k written-out LV URLs, all on third-party pages | **No** |

## Extraction and recognition (black-box)

| Experiment | State | Why incomplete | Implication | Worth finishing? |
|---|---|---|---|---|
| M1 verbatim continuation, random sample | Done: Opus/Sonnet 4.5, Gemini 3.1 Flash-Lite (60+60); Gemini 3 Flash 47 members, no controls | Gemini free quota (20/day); Anthropic credit exhausted | No reproduction anywhere (max 7–13 words, generic or quoted) | **No** |
| M1 on La Contra | Haiku 4.5 (100), Sonnet 4.5 (65), Opus 4.5 (70), Sonnet/Opus 5.5 (100/99) | Anthropic credit exhausted | Even the most-reposted series is not reproduced | **No** |
| M9 sentence-by-sentence (Su et al.) | Llama-3.1-8B base only (La Contra 100+41, random 31) | Local compute time; paid APIs declined | No sentence reproduced | **Only if** a triage signal flags a model, then on that model with a paid key (~$100/model at scale) |
| M9 role-play (Freeman et al.) | Not run | Paid API needed | Adversarial upper bound only | **No** for now |
| M2 DE-COP / M2b pairwise | Done (Claude 4.5 ×3, Gemini 3.1 Flash-Lite) | — | Invalid as evidence: models spot AI rewrites even on unseen text | **No** |

## Answer-time retrieval

| Experiment | State | Why incomplete | Implication | Worth finishing? |
|---|---|---|---|---|
| M4 Gemini URL tool | Done (25 controls × 2 prompts × tools on/off) | — | Fetcher blocked by the site; no reuse; Gemini invents "literal" paragraphs attributed to LV | — |
| M4 search grounding / consumer products | Not run | Billing (Gemini Search), accounts and a counsel-agreed protocol for ChatGPT search, Perplexity, Claude/Gemini web | Untested | **Yes**: low cost (subscriptions), directly observable, separate legal act |

## Token probabilities and collection-level tests (open-weight models)

| Experiment | State | Why incomplete | Implication | Worth finishing? |
|---|---|---|---|---|
| M5 per-article scores + drift calibration | Done (Qwen2.5, Llama-3.1, Mistral, Gemma-2; GPT-2-es and XGLM references) | — | Weak, non-robust signals (AUC ≈ 0.53 after calibration) | — |
| M6 dataset inference (matched, placebos, pre-registered combination) | Done | — | Only Gemma-2 survives matching; explained by knowledge of events (M7) | — |
| M7 neighbour (rewrite) gap | Done (60+60) | — | No wording-specific signal on any model | — |
| M8 Llama-3 vs 3.1 difference-in-differences | Done | — | p = 0.007 in the predicted direction, but knowledge of events can explain it | — |
| M8 + neighbour gap (wording only) | First run done | — | Predicted direction, p ≈ 0.07 (not significant) | — |
| Pre-registered replication of M8 + neighbour (`docs/prereg/`) | Stopped at 247/~810 rewrites, no scoring | Local compute time (two jobs sharing a laptop GPU) | No result yet; only 168 fresh mid-2023 articles were available | **Yes**: the cleanest wording-level design we have; ~1 day locally or a few hours on a rented GPU (~$10–30) |
| Larger open-weight models (70B+) | Not run | Do not fit on the laptop; disk nearly full | Memorization grows with size, so all our open-model nulls are on small models | **Yes, if** the collection-level route is pursued (rented GPU, ~$100–300) |
| Dataset inference with same-period never-crawled controls | Not run | Needs the licensed archive | Would remove the time confound that limits M6/M8 | **Yes**: highest-value design once the archive arrives |

## M10 newspaper-only knowledge (triage)

| Experiment | State | Why incomplete | Implication | Worth finishing? |
|---|---|---|---|---|
| URL / byline / box heading / cloze items | Done on Gemini 3.1 Flash-Lite + 4 local models (60 per group) | — | Exact answers at control rate; cloze guessable from context | — |
| URL number as a date | Gemini 3.1 Flash-Lite, 3.5 Flash-Lite, 3 Flash (20 items) + 4 local | Gemini 3.5–3.8 Flash: 20 requests/day; 2.5: closed; 3.1 Pro: no free tier; Gemma-4: thinking model returns empty answers | All reachable Gemini models know LV's article counter to within days; open models do not. Explainable by third-party URL mentions | **No** (triage signal already obtained; more models would cost money or days) |
| Same-period control with other outlets | Collector written; 28 El Periódico titles + 2,693 (date, ID) pairs | Common Crawl index too slow; FineWeb measurement already answered the question | — | **No** |
| La Contra question → answer recall | Gemini 3.5 Flash-Lite (202+76), Gemma-2 base | Other local models cancelled (weaker in all earlier tests) | No signal (7% vs 7%; hits guessable) | **No** |
| Collection fingerprint (La Contra format, LV house style in generated text) | Designed, not implemented | Session stopped | Cheap (≈30 generations per model per prompt); needs other outlets as controls | **Yes** as a free triage test, if triage continues |

## Not started

| Item | Needs | Worth it? |
|---|---|---|
| ~~Positive control~~ **Done** (see below) | — | — |
| OpenAI models | API key; only black-box tests apply | **Only if** triage continues: the URL test costs cents |
| Copyright traps | Publisher decision; protects only future content | **Yes** (no direct cost; start now) |

## Deadlines (see paper, "Which models can be tested at collection level, and until when")
- Collection-level (probability) tests: open-weight models only (Llama, Gemma, Mistral open, Qwen, DeepSeek, gpt-oss,
  Phi), or closed models through court-ordered expert access. Archive the exact open-weight versions now (repo
  commit + hashes); hosted services and licences can change.
- OpenAI prompt-probability models (davinci-002, babbage-002, gpt-3.5-turbo-instruct) shut down 2026-09-28: closed.
- Claude Sonnet 4.5 API retirement 2026-11-30 (black-box tests on it are already logged in evidence/). Gemini 2.5
  closed to new users. Consider a litigation hold for model versions relevant to a claim.

## Positive control (done 2026-11-26)
| Experiment | State | Implication |
|---|---|---|
| OLMo 2 (infini-gram lookup, `src/olmo_positive_control.py`) | Discarded after 42 articles | Its data is English-filtered: no LV articles, so unusable as positive control (usable as a known-negative) |
| Apertus-8B base (`src/positive_control_apertus.py`, `results/positive_control_apertus.json`) | Done: probabilities on 1,143 + 253 articles, Q→A on 278 | A model trained (almost certainly, via FineWeb-2) on the articles shows no content recall (0/63) and only a faint calibrated collection-level trace (AUC 0.56 vs post-cutoff controls), the same size as Llama/Qwen/Mistral (0.54). Nulls are uninformative about training; faint traces are what training looks like. Caveats: Goldfish loss (no extraction test), FW2 membership assumed through Apertus's filters, same-period split diluted (scan 53%) |
