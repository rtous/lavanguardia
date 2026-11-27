# Handoff: continuing on Google Colab (GPU, more disk)

Read `CLAUDE.md`, `PROGRESS.md` and `docs/experiment_status.md` first. Everything below is resumable.

## State at 2026-11-27 ~23:00 UTC (end of session 11, user asleep) — what to resume
Jobs (all resumable: rerun the same command; each skips finished work):
| Job | Command | State at 23:00 UTC | Needs |
|---|---|---|---|
| M11 run 1 | `export HF_TOKEN=...; ./src/run_colab_m11.sh >> logs/colab_m11.log 2>&1` | Salamandra ~188/200 (finishing ~23:15); a queued relaunch **with** `HF_TOKEN` then runs Llama-3.1-8B-Instruct and Qwen2.5-7B (~10 h each on a T4, may be cut by the VM). Check `wc -l results/m11_nyt_style_*.jsonl` and the log tail | T4, `HF_TOKEN` |
| M12 chain-of-custody re-run (API) | `export GEMINI_API_KEY=...; ./src/run_colab_rerun_custody.sh api >> logs/rerun_custody_api.log 2>&1` | 3.5-FL 61/426, 3.1-FL 39/426 (free daily quota) | after ~08:00 UTC |
| M11 chain-of-custody re-run | — | **Done: 117/117 identical** | — |
| FineWeb-2 copy counts + top-20 check | — | **Done** (`results/fw2_most_copied.md`, paper Table "most-copied") | — |
| Always alongside | `./src/colab_sync.sh loop 300 &`, `GH_TOKEN=... ./src/autosave.sh 600 &` | — | `GH_TOKEN` for push |

Resume tomorrow: follow "Quick resume" below (clone from GitHub, `./src/colab_sync.sh restore`, gunzip the hit lists),
then restart the sync loop + autosave, then the two jobs above. GitHub holds every result row and doc; Drive holds the
untracked `evidence/` raw logs (incl. `evidence/m11_nyt_style/`, `evidence/m11_nyt_style_rerun/`), `data/` (incl.
`fw2_cluster_sizes/`, `fw2_top_text.json`, `fw2_sample2020.json`) and `logs/`. If the VM died mid-run, run
`python -I src/evidence_audit.py` after restore to check every result row still has its raw record.

After they finish:
- `python -I src/m12_url_reverse.py compare` → `results/rerun_custody/`; report agreement in paper + `docs/evidence_gaps.md`.
- `python -I src/m11_nyt_style.py summary` → paper M11 section.
- Design the pre-registered most-copied extraction test on `results/fw2_most_copied_checked.json` (controls:
  post-cutoff articles with comparable copy counts, counted in later Common Crawl captures). Text of the top 30 is in
  `data/fw2_top_text.json` (gitignored; regenerate with `python -I src/fw2_top_check.py`).
**Important on restore:** the full FineWeb-2 hit lists (`results/dataset_presence_hits_{spa,cat}_Latn.jsonl`,
gitignored) are NOT complete in the 26-Nov extras zip (164,568 of 310,502 Spanish hits). Full copies:
`MyDrive/lavanguardia_work/data/hits_{spa,cat}_Latn.jsonl.gz` (SHA-256 in `MANIFEST.txt`) — gunzip into `results/`.
Check: Spanish 310,502 lines / 303,226 distinct URLs / 146 shards; Catalan 17,947 lines.
Per-shard copy counts done so far are in `data/fw2_cluster_sizes/` (mirrored to Drive by `colab_sync.sh`).
Before closing the tab on purpose: `from google.colab import drive; drive.flush_and_unmount()`.

## Quick resume (since 2026-11-27): GitHub first, then Drive for the untracked folders
**Do not rsync the whole Drive mirror over the repo.** On 2026-11-27 the VM died while Drive was still ~1.5 h behind,
and Drive held older, shorter copies than GitHub (see `docs/evidence_gaps.md`). Instead:
```python
from google.colab import drive, userdata; drive.mount('/content/drive')
import os; os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN')
```
```bash
cd /content && git clone https://github.com/rtous/lavanguardia.git && cd lavanguardia && chmod +x src/*.sh
./src/colab_sync.sh restore                 # data/ evidence/ logs/ only; warns about stale Drive files
(cd results && for L in spa_Latn cat_Latn; do gunzip -c /content/drive/MyDrive/lavanguardia_work/data/hits_$L.jsonl.gz > dataset_presence_hits_$L.jsonl; done)
python -I src/evidence_audit.py             # result rows without a raw evidence record
pip install -q -r requirements.txt bitsandbytes
nohup ./src/colab_sync.sh loop 300 >> logs/colab_sync.log 2>&1 &
```
Before closing the browser on purpose, run `from google.colab import drive; drive.flush_and_unmount()` in a cell:
it waits until Drive has uploaded everything.

## Older quick resume (state at 2026-11-26 22:30 UTC)
All jobs were stopped at the end of the session. Done: Llama replication, Salamandra, FineWeb-2 scan, positive control.
Only open experiment: **M11 NYT-style extraction**, stopped at 7/200 articles on the first model (resumable, skips the 7).
To continue it: run the cell below, but launch `nohup ./src/run_colab_m11.sh >> logs/colab_m11.log 2>&1 &` instead of
`run_colab_resume.sh`, and start `nohup ./src/colab_sync.sh loop 300 >> logs/colab_sync.log 2>&1 &` first. ~14 h on a T4.
After restoring from Drive run `chmod +x src/*.sh` (Drive drops the exec bit) and delete any `.last_sync_utc` in the repo.

## Previous quick resume (state at 2026-11-26 ~18:00 UTC; done)
Pending, both resumable: (1) Llama 3 vs 3.1 neighbour replication (rewrites ~80% done, then scoring + DiD);
(2) Salamandra-7B Q->A + URL number (610/878). Done: FineWeb-2 scan, positive control, Salamandra probabilities.
One-time: in Colab's Secrets panel (key icon) add `HF_TOKEN` (Llama licence is granted to account rtous) and enable
notebook access. Then run this single notebook cell on a GPU runtime (T4 is fine):
```python
from google.colab import drive, userdata; drive.mount('/content/drive')
import os; os.environ['HF_TOKEN'] = userdata.get('HF_TOKEN')
!rsync -rlt /content/drive/MyDrive/lavanguardia_work/colab_state/lavanguardia/ /content/lavanguardia/
!cd /content/lavanguardia && pip install -q -r requirements.txt bitsandbytes
!cd /content/lavanguardia && nohup ./src/run_colab_resume.sh > logs/colab_resume.log 2>&1 &
```
Progress: `!tail -3 /content/lavanguardia/logs/colab_resume.log /content/lavanguardia/logs/colab_queue4.log`.
Model weights (~45 GB) re-download automatically. When "RESUME done" appears: analyse results (see PROGRESS.md "Next").

## Resume after a Colab disconnect (session state is mirrored to Drive)
The whole working tree (code incl. uncommitted edits, `.git`, `data/`, `evidence/`, `logs/`, `results/`) is mirrored
to `MyDrive/lavanguardia_work/colab_state/lavanguardia/` every 5 min by `src/colab_sync.sh loop`. To resume:
```python
from google.colab import drive; drive.mount('/content/drive')
```
```bash
rsync -rlt /content/drive/MyDrive/lavanguardia_work/colab_state/lavanguardia/ /content/lavanguardia/
cd /content/lavanguardia && pip install -q -r requirements.txt bitsandbytes
nohup ./src/colab_sync.sh loop 300 > logs/colab_sync.log 2>&1 &     # restart the mirror first
tail logs/colab_*.log                                                # see which job was running, then rerun it
```
All `run_colab_*.sh` jobs are resumable: rerun the same script. Model weights are not mirrored (re-download from HF).

## Setup (first time only; superseded by the resume block above once colab_state/ exists)
```bash
git clone https://github.com/rtous/lavanguardia.git && cd lavanguardia
pip install -r requirements.txt          # mlx-lm is skipped on Linux
```
- **Data is not in git.** It is on Google Drive (account ruben.tous.2@gmail.com), folder `lavanguardia_work/data/`:
  `data_20261126.zip` (unzip into the repo root: `data/cc`, `data/m10`, `data/decop`), `evidence_backup_20261126.zip`
  (read-only backup), `extras_20261126.zip` (logs + FineWeb-2 hit lists, unzip into the repo root) and `MANIFEST.txt`
  (source commit and SHA-256 of every file). In Colab:
  ```python
  from google.colab import drive; drive.mount('/content/drive')
  ```
  ```bash
  W=/content/drive/MyDrive/lavanguardia_work/data
  (cd $W && grep '\.zip$' MANIFEST.txt | head -3 | sha256sum -c)   # check the zips against the manifest
  unzip -q $W/data_20261126.zip && unzip -q $W/extras_20261126.zip
  ```
  API keys: use Colab's Secrets panel (e.g. `GEMINI_API_KEY`, `HF_TOKEN`), not a `.env` on Drive.
- **Evidence logs** (`evidence/`, ~35 MB, append-only) stay on the Mac as the master copy. On Colab new calls are
  appended to a fresh `evidence/`; copy those files back and append them to the master. Never edit existing lines.
- Gated models (Llama) need a Hugging Face token and accepted licence: `huggingface-cli login`.
- `.env` (API keys) is not needed for open-weight work.

## GPU precision (Colab T4 = 15 GB, no native bf16)
`src/hf_load.py` (used by `m5_hf.py` and `probe.ask_hf`): `--precision` or env `HF_PRECISION` = auto|bf16|fp16|int8|int4.
auto = bf16 on A100/L4, fp16 on T4. 7-8B models need int8 on a T4. Precision + weights commit are written to every
result row / evidence record. Check on GPT-2-es (2 articles): int8 within ~0.005 nats of fp16, int4 within ~0.05.

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

## Autosave (unattended sessions, added 2026-11-27)
`GH_TOKEN=<token> nohup ./src/autosave.sh 600 >> logs/autosave.log 2>&1 &` commits new M11/M12 result rows, pushes to
GitHub and mirrors to Drive every 10 min. The token is only on the push command line (never in `.git/config`).
