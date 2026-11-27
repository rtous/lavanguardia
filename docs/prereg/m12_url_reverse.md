# Pre-registration: M12, reverse URL test (from article ID to article)

Written 2026-11-27, before any reverse query was sent to any model. The git commit of this file timestamps the plan.

**Why.** M10 found that Gemini models predict La Vanguardia's numeric article IDs to within 2–4 days (open models:
65–900+ days). Two explanations:
- (H-links) Gemini estimates between IDs it saw written out on third-party pages. That teaches the date→ID pattern
  but not which article carries which ID.
- (H-pages) Gemini saw LV pages together with their URLs, e.g. because Google's crawl keeps each page's URL.
  That ties each ID to its article.
Only H-pages lets a model go back from an ID to a specific article. This test checks that.

**Data** (`data/m12/pairs.jsonl`, built by `python -I src/m12_url_reverse.py build`, sha256
`009396f926e8b128bfca28541d6a1a80678005716c73acee29c9e32e8fa9aef5`). Source: the M10 `url_id` items (La Vanguardia
only, La Contra excluded). For every (set, publication date, section) with at least two articles, the two lowest
IDs form a pair. 117 member pairs (2020–2023) and 96 control pairs (Sep 2025–Mar 2026, after the training data of the
models tested).

**Procedure.** For each article in a pair, one query (temperature 0, no tools, so no browsing):
> ¿Cuál es el titular del artículo de La Vanguardia publicado en esta URL?
> https://www.lavanguardia.com/{section}/{date}/{ID}/
> Responde solo con el titular exacto, sin explicaciones. Si no estás seguro, da igualmente tu mejor respuesta.

The title words (slug) are removed from the URL. Members and controls get identical treatment. Every call is logged
in `evidence/m12_url_reverse/` (append-only).

**Score.** Overlap = share of the title's content words (≥4 letters, not stopwords, not numbers, not the section
name) that appear in the answer. Each answer is scored against its own title and against the partner's title.
Pair score = mean over the two answers of (overlap with own title − overlap with partner's title).
If the model uses only the date and section, the two answers are exchangeable and the expected pair score is exactly 0.

**Models.** Primary: `gemini-3.5-flash-lite` (the most precise model in M10; free tier). Replication, run
afterwards and reported separately: `gemini-3.1-flash-lite`. Others (open models on the GPU, other Gemini versions,
other providers) are exploratory.

**Primary test** (primary model, members): pair score > 0, one-sided Wilcoxon signed-rank, α = 0.05.
**Required for a positive reading:** controls show no such effect (control pair score not significant), and members
exceed controls (one-sided Mann–Whitney on pair scores, α = 0.05).
**Secondary:** answers with overlap ≥ 0.8 with their own title, members vs controls (one-sided Fisher); every such
member answer listed with its true title, and checked for third-party pages linking that URL before it is described.
For the 60 member articles that also have an M10 forward answer, the relation between forward ID error and reverse
overlap is reported descriptively.

**Reading.**
- Positive (members > 0 and > controls): the ID points the model to the specific article → it saw LV URLs paired with
  their articles (H-pages, or third-party links whose anchor text is the headline: checked per hit). Evidence of
  exposure to LV pages, not of memorized wording.
- Null: the ID-to-date skill is a general pattern (consistent with H-links). It does not rule out training on the pages.
- Members > 0 but controls also > 0: a design leak (e.g. ID order within a day tracks topic); no conclusion.

**Not part of this pre-registration.** The re-analysis of the existing M10 forward answers by error in IDs (instead
of days) uses data already seen and is reported as exploratory.

## Amendment 1 (2026-11-27, before any query on a member pair)
- The prompt above (v1) was sent for 2 control articles (first pair) on `gemini-3.5-flash-lite`. Both answers were
  "I cannot access the internet / visit URLs". The question was read as "visit this link".
- New prompt (v2, `PROMPT_VERSION = 2` in `src/m12_url_reverse.py`), used for all pairs and both models:
  > No hace falta que accedas a internet: responde de memoria. El artículo de La Vanguardia con el número {ID},
  > publicado el {fecha} en la sección «{section}», tiene una URL que empieza por https://www.lavanguardia.com/{section}/{date}/{ID}/
  > ¿Cuál es su titular? Responde solo con el titular, sin explicaciones. Si no estás seguro, da igualmente tu mejor suposición.
- Pilot of v2 (not analysed): the same 2 controls ("no information about that future date": the expected control
  answer) and 3 member articles that are NOT in any pair (`evidence/m12_pilot/`): real guesses, topical for the date,
  overlap 0, 0, 0.17. v1 rows stay in the results file with `prompt_version` 1 and are excluded from the summary.
- Refusals and "I don't know" answers score 0 against both titles, so they cannot create a pair effect.
- Everything else (pairs, score, tests, reading) unchanged.
