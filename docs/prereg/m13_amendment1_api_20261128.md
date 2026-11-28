# M13 amendment 1 (2026-11-28, before any API query): Claude Opus 4.5 and Gemini 3.1 Flash-Lite

Applies to `docs/prereg/m13_most_copied.md`. Committed before the first API query of M13.

**Models and why these.** Controls must be published after the model's *training data* cutoff (CLAUDE.md).
- `claude-opus-4-5-20251101` (Anthropic): training data cutoff Aug 2025 (platform.claude.com model page, read
  2026-11-28). Our controls are Sep 2025–Mar 2026. The current Claude models (Opus/Sonnet/Haiku 5.5) have a training
  data cutoff of Jun 2026, after all our controls, so they are **not** tested here (no valid control set).
- `gemini-3.1-flash-lite` (Google): knowledge cutoff Jan 2025 (Google model card; used with the same controls in M2/M10/M12).

**Procedure.** M13's prompt text, windows, prefix length, number of attempts (10), 256 output tokens and scoring,
unchanged. Differences forced by the APIs:
- *Claude*: the API (version 2026-10-21) rejects `temperature`/`top_p`, so the 10 attempts are 10 independent samples at
  the API's default decoding (no greedy attempt, no seed). Extended thinking off (Opus 4.5 default).
- *Gemini*: attempt 1 at temperature 0; attempts 2–10 at temperature 0.8, top_p 0.95, seed = (article ID + offset + i).
  The API does not guarantee determinism even with a seed.
- Output length: 256 tokens on Claude; Gemini keeps `src/probe.py`'s 2,048-token floor (as in every earlier Gemini
  run), the same for most-copied articles and controls; scoring is against the same next 250 words.
- One API call per attempt; each call is one evidence record (`evidence/m13_most_copied/calls.jsonl`); the result row
  lists the 10 record hashes.
- The fake assistant acknowledgement stays a middle turn (no final-turn prefill).

**Controls** (no M11 runs exist on these models): offset 0 on the first 20 La Contra and first 20 random M11 controls
(M11's order and filters), plus M13's 20 offset controls at offset 300. Same prompts and attempts.

**Outcomes.** As M13: primary = most-copied (offset 0) > these 40 controls, one-sided Mann–Whitney, per model,
α = 0.05 / 2 for the two API models (reported separately from the open models). Secondary as M13, plus per set:
share of attempts refused or empty, and (Gemini) share of attempts stopped with finish reason `RECITATION`
(Google's filter for output that recites a source). Recitation stops are reported, not counted as matches: Google's
check compares against its web index, so a stop shows the output resembled some public text, not where the model
learned it.

**Size and cost.** 104 prompts (44 most-copied windows, 40 offset-0 controls, 20 offset controls) × 10 attempts
= 1,040 calls per model. Claude Opus 4.5 at ≤ 700 input + 256 output tokens per call: ≤ US$10.
The run stops if the provider reports a quota or billing error; completed rows are reported as such.
