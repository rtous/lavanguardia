#!/usr/bin/env bash
# Colab port of src/run_queue4.sh: pre-registered replication of the neighbour-DiD (docs/prereg/did_neighbour_replication.md).
# Deviations from the registered MLX setup are recorded in the prereg file BEFORE scoring (see its "Deviations" section).
# Sequential, one GPU job, resumable. Needs HF_TOKEN with the Llama 3 / 3.1 licences accepted.
# The NEW2 article set (data/cc/mid2023_rep.jsonl, 168 fresh articles) is frozen: the CC fetch step is NOT rerun.
# Log: logs/colab_queue4.log. Run src/colab_sync.sh loop alongside.
set -eu   # stop at the first failure (e.g. Llama licence not yet granted); rerun to resume
cd "$(dirname "$0")/.."
export HF_PRECISION=${HF_PRECISION:-int4}   # nf4 4-bit, closest to the registered MLX 4-bit models
P=data/decop/paraphrases_mid2023_rep_hf.jsonl   # new file; the 247 MLX rewrites stay untouched in paraphrases_mid2023_rep.jsonl
echo "=== $(date -u +%FT%TZ) rewrites (Qwen2.5-7B-Instruct, $HF_PRECISION)"
python -I src/local_paraphrase.py --model hf:Qwen/Qwen2.5-7B-Instruct --rep --out $P
echo "=== $(date -u +%FT%TZ) score Llama-3.1-8B"
python -I src/m5_neighbour.py --model hf:meta-llama/Llama-3.1-8B --src $P:local --out results/m5_neighbour_mid2023rep_hf_llama31_8b.jsonl
echo "=== $(date -u +%FT%TZ) score Llama-3-8B"
python -I src/m5_neighbour.py --model hf:meta-llama/Meta-Llama-3-8B --src $P:local --out results/m5_neighbour_mid2023rep_hf_llama3_8b.jsonl
echo "=== $(date -u +%FT%TZ) DiD"
python -I src/did_neighbour.py --l3 results/m5_neighbour_mid2023rep_hf_llama3_8b.jsonl --l31 results/m5_neighbour_mid2023rep_hf_llama31_8b.jsonl --out results/did_neighbour_rep.json
echo "=== $(date -u +%FT%TZ) QUEUE4 done"
