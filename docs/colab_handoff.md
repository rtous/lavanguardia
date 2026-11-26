# Handoff: continuing on Google Colab (GPU, more disk)

Read `CLAUDE.md`, `PROGRESS.md` and `docs/experiment_status.md` first. Everything below is resumable.

## Setup
```bash
git clone https://github.com/rtous/lavanguardia.git && cd lavanguardia
pip install -r requirements.txt          # mlx-lm is skipped on Linux
```
- **Data is not in git** (`data/` is gitignored, ~20 MB: Common Crawl article texts + M10 items). Copy it from the Mac
  (e.g. zip `data/` to Google Drive, then unzip into the repo). Needed: `data/cc/*.jsonl`, `data/m10/items.jsonl`,
  `data/decop/` (for the replication).
- **Evidence logs** (`evidence/`, ~35 MB, append-only) stay on the Mac as the master copy. On Colab new calls are
  appended to a fresh `evidence/`; copy those files back and append them to the master. Never edit existing lines.
- Gated models (Llama) need a Hugging Face token and accepted licence: `huggingface-cli login`.
- `.env` (API keys) is not needed for open-weight work.

## What runs on a CUDA GPU
| Script | Colab? | How |
|---|---|---|
| `src/m5_hf.py` (word-probability scores) | yes | `--model <HF repo id>`; bf16 on CUDA |
| `src/probe.py` generation | yes | model id `hf:<HF repo id>` (transformers, greedy, weights commit hash logged) |
| `src/m10_exclusive_facts.py run` (URL/Q→A items) | yes | `--model hf:<repo>`; base models are continued as raw pages automatically |
| `src/m1_continuation.py`, `src/m9_decomposition.py` | yes | pass `--model hf:<repo>` |
| `src/m5_logprob.py`, `src/m5_neighbour.py`, `src/local_paraphrase.py` | **no** (MLX) | port to transformers first (see replication) |
| analysis scripts (`positive_control_apertus.py`, `did_*.py`, `di_*.py`) | yes | CPU only |

## Priorities (see the paper, "Promising avenues" and "Which models can be tested")
0. **Finish the FineWeb-2 Spanish scan** (`python -I src/dataset_presence.py --config spa_Latn --shards 999`, resumable;
   then `src/presence_overlap.py`, then `src/positive_control_apertus.py`). Gives clean same-period in/out groups for
   the Apertus positive control and for any model trained on FineWeb-2. Bandwidth only, ~8 h on a laptop, faster on Colab.
1. **BSC Salamandra-7B base** (`BSC-LT/salamandra-7b`, ~16 GB bf16; Spanish/Catalan, Common Crawl in its data):
   ```bash
   python -I src/m5_hf.py --model BSC-LT/salamandra-7b --inputs data/cc/members.jsonl:member data/cc/controls.jsonl:control --out results/m5_salamandra7b.jsonl
   python -I src/m5_hf.py --model BSC-LT/salamandra-7b --inputs data/cc/lacontra_members.jsonl:member data/cc/lacontra_controls.jsonl:control --out results/m5_lacontra_salamandra7b.jsonl
   python -I src/m10_exclusive_facts.py run --model hf:BSC-LT/salamandra-7b --types qa url_id --n 300
   python -I src/positive_control_apertus.py   # in-FineWeb-2 vs not-found split, calibrated with GPT-2-es
   ```
   Interpret against the Apertus positive control (results/positive_control_apertus.json).
2. **ALIA-40b** (`BSC-LT/ALIA-40b`; `BSC-LT/salamandra-40b` redirects to it): 80 GB in bf16, so an
   A100-80GB or 8-bit loading (add bitsandbytes `load_in_8bit` to `m5_hf.py`; record the quantization in results).
3. **Pre-registered Llama-3 vs 3.1 replication** (`docs/prereg/did_neighbour_replication.md`, `src/run_queue4.sh`):
   rewrites stopped at 247/~810 (`data/decop/paraphrases_mid2023_rep.jsonl`). Port `local_paraphrase.py` and
   `m5_neighbour.py` to transformers. The pre-registration fixed the 4-bit MLX models: if bf16 HF weights are used,
   record it as a deviation in the prereg file **before** scoring, or keep the rewriter identical
   (Qwen2.5-7B-Instruct) and only change precision of the scorers, stated in advance.
4. **Larger open models** (Llama-3.1-70B, Gemma-2-27B, Qwen2.5-72B) with `m5_hf.py` + 4/8-bit loading.
5. **Archive the exact open-weight versions tested** (repo + commit hash, logged automatically by `ask_hf`).

## Do not
- Do not commit `data/`, `evidence/` or `.env`. The GitHub repo is **public**.
- Do not run several GPU jobs in parallel or make queues wait on `pgrep -f` (see CLAUDE.md).
