# Evidence gaps (chain of custody)

Raw query records (`evidence/`, append-only, gitignored) that were made but did not survive. The result rows
themselves are intact (committed to git by `src/autosave.sh`, with prompt, full model output and the SHA-256 of the
missing raw record), but there is no raw record to check that hash against. Check at any time with
`python -I src/evidence_audit.py` (→ `results/evidence_audit.json`).

## 2026-11-27: Colab VM lost before Drive finished uploading
- **What happened.** Session 10 ran on Colab from 09:23 UTC. `evidence/` lived on the VM's local disk and was mirrored to
  Google Drive every 5–10 min (`src/colab_sync.sh`). The VM was recycled some time after 11:33 UTC. Drive uploads
  asynchronously, and what reached Drive was an older, line-complete *prefix* of each file (the first 22 M11 records,
  the first 38 M12 records), plus a `.git` with missing objects. Result rows had been pushed to GitHub every 10 min,
  so GitHub holds more rows than Drive holds raw records.
- **Checked on 2026-11-27 (session 11):** every Drive row is byte-identical to the corresponding committed row
  (prefix, no edits); every surviving raw record parses; data inputs match `MANIFEST.txt` and the pre-registered
  `data/m12/pairs.jsonl` hash (`009396f9…`, rebuilt deterministically).
- **Rows without a raw record:**

| Results file | Rows | With raw record | Without |
|---|---|---|---|
| `m11_nyt_style_salamandra-7b-instruct.jsonl` | 117 | 22 (rows 0–21) | 95 (rows 22–116) |
| `m12_url_reverse_gemini-3.5-flash-lite.jsonl` | 428 | 38 (rows 0–37) | 390 |
| `m12_url_reverse_gemini-3.1-flash-lite.jsonl` | 426 | 0 | 426 |
| `m10_exclusive_salamandra-7b.jsonl` (2026-11-26) | 878 | 878 | 0 |

- **Treatment.** Raw logs were not reconstructed from result rows (that would be a derived record presented as raw).
  Options: (a) report these rows with this note attached; (b) re-run the same queries with new raw records, keep the
  originals, and report agreement between the two runs (Gemini at temperature 0 is not guaranteed deterministic;
  the Salamandra runs use a fixed seed per article).
- **Fix against recurrence.** `src/colab_sync.sh restore` (copies only untracked folders and never overwrites with an
  older or shorter file; flags stale Drive copies). Drive alone is not a reliable copy of the last hours of a session.

## Re-run status (2026-11-27 21:50 UTC)

- **M11 Salamandra: complete, 117/117 identical to run 1** (every attempt's score, the greedy output and the best
  verbatim match outside quotes; `results/rerun_custody/m11_compare.json`). The 95 unbacked run-1 rows are now backed
  by a byte-for-byte reproducible re-run with full raw records in `evidence/m11_nyt_style_rerun/`.
- **M12 Gemini: partial (free daily quota).** gemini-3.5-flash-lite 61/426 (0 identical texts, 57/61 same pair score);
  gemini-3.1-flash-lite 39/426 (39/39 identical). Resume with `./src/run_colab_rerun_custody.sh api` after ~08:00 UTC.

## 2026-11-28: Google Drive quota full, then VM lost overnight
- **What happened.** Drive (15 GB, shared with other projects) filled up on 2026-11-27; the last successful mirror is
  stamped 21:53:52 UTC. Uploads failed silently after that, and the VM was recycled overnight. Result rows kept reaching
  GitHub (autosave), raw records did not reach Drive.
- **Lost raw records** (result rows intact in git; checked with `python -I src/evidence_audit.py` on 2026-11-28):
  - `m11_nyt_style_salamandra-7b-instruct.jsonl`: 200 rows, 22 with raw record (rows 0–21), 178 without.
  - `m11_nyt_style_Qwen2.5-7B-Instruct.jsonl`: 48 rows, 0 with raw record.
  - **Amendment 1's re-run lost all of its raw records**: `evidence/m11_nyt_style_rerun/` and
    `evidence/m12_url_reverse_rerun/` exist on Drive but hold no `calls.jsonl`. So the statement above ("now backed by
    ... full raw records in `evidence/m11_nyt_style_rerun/`") no longer holds: the 117/117 identity with run 1 was
    observed and is recorded in `results/rerun_custody/m11_compare.json`, but those records are gone.
- **Treatment.** Custody re-run 2 (`docs/prereg/amendment_rerun_custody2_20261128.md`) into `results/rerun_custody2/`,
  `evidence/*_rerun2/`. Storage fix: `src/autosave.sh` pushes `evidence/` to a private GitHub repository every 10 min.
