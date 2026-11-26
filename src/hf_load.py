"""Load a Hugging Face causal LM with an explicit, recorded precision (shared by m5_hf.py and probe.ask_hf).

precision: auto | bf16 | fp16 | int8 | int4   (default: env HF_PRECISION, else auto)
  auto = bf16 on GPUs that support it (A100, L4), fp16 on those that don't (T4), float32 on CPU/MPS.
  int8 / int4 = bitsandbytes quantization (CUDA only), for models that do not fit in 16-bit, e.g. a 7-8B model on a
  15 GB T4. Quantization slightly changes token probabilities, so the precision is returned and must be written to
  every output row; compare models scored at different precisions with that in mind.
Returns (model, tokenizer, info) with info = {"precision", "revision"} (revision = weights commit hash).
"""
import os

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


def device():
    if torch.cuda.is_available():
        return "cuda"
    return "mps" if torch.backends.mps.is_available() else "cpu"


def resolve_precision(precision=None):
    p = (precision or os.environ.get("HF_PRECISION") or "auto").lower()
    if p == "auto":
        dev = device()
        if dev != "cuda":
            return "fp32"
        return "bf16" if torch.cuda.is_bf16_supported(including_emulation=False) else "fp16"
    assert p in ("bf16", "fp16", "fp32", "int8", "int4"), f"unknown precision {p}"
    return p


def load(repo, precision=None):
    p = resolve_precision(precision)
    dev = device()
    kw = {}
    if p in ("int8", "int4"):
        assert dev == "cuda", "bitsandbytes quantization needs a CUDA GPU"
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = (BitsAndBytesConfig(load_in_8bit=True) if p == "int8" else
                                     BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                                        bnb_4bit_compute_dtype=torch.float16))
        kw["device_map"] = {"": 0}
    else:
        kw["torch_dtype"] = {"bf16": torch.bfloat16, "fp16": torch.float16, "fp32": torch.float32}[p]
    tok = AutoTokenizer.from_pretrained(repo)
    model = AutoModelForCausalLM.from_pretrained(repo, **kw)
    if "device_map" not in kw:
        model = model.to(dev)
    try:
        from huggingface_hub import HfApi
        rev = HfApi().model_info(repo).sha
    except Exception:
        rev = "unknown"
    return model.eval(), tok, {"precision": p, "revision": rev}
