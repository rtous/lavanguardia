# Amendment (2026-11-27, before any re-run query): chain-of-custody re-run of M11 and M12

Applies to `docs/prereg/m11_nyt_style.md` and `docs/prereg/m12_url_reverse.md`. Committed before the first query below.

**Why.** Raw evidence records were lost for 95 M11 rows and 816 M12 rows when a Colab VM died before Google Drive
finished uploading (`docs/evidence_gaps.md`). The result rows survive in git, but no raw record backs them.

**What is re-run.** Same code, prompts, decoding parameters and seeds as run 1, with only the output locations changed
(`--rerun`): results in `results/rerun_custody/`, raw records in `evidence/<exp>_rerun/calls.jsonl`. Run 1 files are
left untouched.
- M12: every query of run 1, on both models (gemini-3.5-flash-lite: 426 queries; gemini-3.1-flash-lite: 426),
  temperature 0 as in run 1. The pair file is the pre-registered one (sha256 `009396f9…`, rebuilt deterministically).
- M11: the 117 Salamandra-7B-Instruct articles run 1 did (60 La Contra members, 57 controls), same order,
  same per-article torch seed, int4 on a T4. The remaining articles and models continue later in run 1's file, as
  pre-registered.

**How it is reported.**
- The pre-registered analyses stay as specified on run 1 (the rows that hold the reported numbers).
- Each re-run gets the same pre-registered statistics, computed separately (never pooled with run 1), and the
  agreement with run 1: share of identical answers (M12), identical attempt scores and best LCS per article (M11).
- If the re-run changes a conclusion (significance at the pre-registered α, or any article/answer crossing a
  pre-registered threshold), both runs are reported, and the re-run (fully backed by raw records) is the one cited in the
  court-facing text.
- Expected differences: Gemini does not guarantee determinism at temperature 0, and the API model behind the same ID
  may have changed. Local generation can differ across library versions (this run: torch 2.14.1+cu130,
  transformers 5.22.1; run 1's versions were not logged) and GPU kernels.
