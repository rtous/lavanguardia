# CLAUDE.md — La Vanguardia vs. commercial AI: evidence of training use

## Goal
Produce **court-presentable evidence** that articles from *La Vanguardia* (Grupo Godó) are being, or have been,
used by one or more commercial AI systems (ChatGPT/OpenAI, Gemini/Google, Claude/Anthropic, Meta AI, Mistral,
Grok, Perplexity, DeepSeek, Qwen…). The audience is a **judge, not a peer reviewer**. Prefer methods that are
simple to explain, visually convincing, reproducible, and backed by a basic statistical control. Do not chase rigor for its own sake.

Two distinct things can be shown, and we keep them apart in every report:
1. **Training use (memorization)**: the model reproduces or recognizes article text it could only know from training.
2. **Retrieval use (RAG/browsing)**: the product fetches and reuses articles at answer time, for example Perplexity
   or ChatGPT search. This is a different legal act, so it needs separate tests with browsing ON vs. OFF.

## Ground rules (non-negotiable)
- **No unauthorized access.** Do not bypass paywalls, logins, rate limits or robots rules on lavanguardia.com,
  and do not use pirate mirrors. Evidence obtained that way can be inadmissible and can expose the client.
  Sources we may use: articles supplied by La Vanguardia (expected: thousands), public pages, **Common Crawl**
  (public, and itself the main LLM training source), and the Internet Archive.
- **Chain of custody.** Every model query is logged with timestamp, provider, exact model ID/version, parameters
  (temperature, etc.), full prompt, full raw response and a SHA-256 hash. Logs are append-only JSONL under
  `evidence/`. Never edit a raw log. Derived analyses go to `results/`.
- **Controls are mandatory.** Every positive test is paired with a control set: articles published **after** the
  model's training cutoff, or comparable text from a non-crawled source. The judge must see "it reproduces ours
  but not texts it couldn't have seen."
- **Prefer black-box, API-only methods** (commercial models rarely expose logprobs). Use logprob methods only where available.
- Use deterministic settings (temperature 0) where possible, and record when the API does not guarantee determinism.
- Keep secrets (API keys) in `.env` (gitignored). Never commit them.
- Language: code/docs in English; reports for court may be drafted in Spanish/Catalan.

## Repo layout (planned; create as needed)
- `docs/` — literature review, methodology, legal context
- `data/` — article corpora (gitignored if licensed/large): `data/lavanguardia/`, `data/proxy/` (other outlets), `data/controls/`
- `src/` — Python code (prober clients, tests, metrics)
- `evidence/` — raw, hashed, append-only query logs
- `results/` — tables, plots, per-method summaries
- `PROGRESS.md` — **always update at the end of a work session**: what was done, findings, next steps.

## Methodological rules learned (see PROGRESS.md for evidence)
- Absolute DE-COP accuracy is NOT evidence: frontier models spot LLM-written paraphrases even on unseen text. Only
  member-minus-control differences count. Never use 4-option minimal-edit variants (majority-vote leak); use pairwise.
- Logprob signals must be drift-corrected with a reference model whose data predates both sets (e.g. flax-community/gpt-2-spanish, data 2018).
- Controls must be published after the target model's *training data* cutoff (not just its "reliable knowledge" cutoff).
- Facts ≠ wording: knowing the events of an article proves nothing.

## Working conventions
- Python 3, small scripts, `requirements.txt`. Run Python that reads downloaded data with `python -I`.
- Each experiment = one script + one config + one results folder, so it can be rerun by a court expert.
- Before starting work, read `PROGRESS.md`; after finishing, update it.
