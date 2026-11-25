#!/bin/sh
# Waits for the Gemini free-tier reset (09:00 CET, 2026-11-26), then: M9 decomposition pilot, then M1 on Gemini 3 Flash.
until [ "$(date +%Y%m%d%H%M)" -ge 202611260901 ]; do sleep 60; done
set -x
.venv/bin/python -I src/m9_decomposition.py --model gemini-3.1-flash-lite --n 60 --k 4 --workers 2
.venv/bin/python -I src/m1_continuation.py --model gemini-3-flash-preview --n 60 --workers 1
echo DAY3 done
