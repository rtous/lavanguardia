# Amendment 2 (2026-11-28, before any query below): chain-of-custody re-run 2 of M11 and M12

Applies to `docs/prereg/m11_nyt_style.md`, `docs/prereg/m12_url_reverse.md` and amendment 1
(`amendment_rerun_custody_20261127.md`). Committed before the first query below.

**Why.** Google Drive reached its storage quota on 2026-11-27 (exact time unknown; the last successful mirror is stamped
21:53:52 UTC). From then on `src/colab_sync.sh` could not upload, and the VM was lost overnight. Raw records that were
written only to the VM disk were lost again (`docs/evidence_gaps.md`, section 2026-11-28):
- M11 run 1: Salamandra rows 22–199 (178 rows) and all 48 Qwen2.5 rows have no raw record (only rows 0–21 do).
- Amendment 1's re-run: none of its raw records survived (`evidence/m11_nyt_style_rerun/` and
  `evidence/m12_url_reverse_rerun/` are empty on Drive). Its 117 M11 rows and 102 M12 rows are in git, without records.

**What is re-run.** Same code, prompts, decoding parameters and seeds as run 1 (`--rerun`, as in amendment 1), into new
locations so that nothing earlier is touched: results in `results/rerun_custody2/`, raw records in
`evidence/<exp>_rerun2/calls.jsonl` (`RERUN_DIR=results/rerun_custody2 RERUN_SUFFIX=_rerun2`).
- M11: every article run 1 holds when the re-run starts, per model (Salamandra-7B-Instruct: 200; Qwen2.5-7B-Instruct:
  the rows present then), same order, same per-article seed, int4 on a T4. Rows 0–21 of Salamandra (which have raw
  records) are included on purpose: they test whether the re-run reproduces run 1 exactly.
- M12: every query of run 1 on both Gemini models, when an API key is available (not before).

**Storage fix (from now on).** `evidence/` is pushed every 10 minutes to a private GitHub repository by
`src/autosave.sh` (once a push is acknowledged, the records no longer depend on the VM or Drive). Drive stays as a
second copy. `src/evidence_audit.py` is run at the start of every session.

**How it is reported.** As amendment 1: pre-registered analyses stay on run 1; each re-run is analysed separately,
never pooled; agreement with run 1 is reported; if a re-run changes a conclusion, both are reported and the fully
recorded re-run is cited in the court-facing text. Amendment 1's re-run rows are kept and reported as a run without
raw records.
