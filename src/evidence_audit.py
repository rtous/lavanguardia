"""Check which result rows have their raw query record in evidence/ (chain of custody).

Each result row stores the SHA-256 of its raw evidence record (field `evidence_sha256` or `sha256`). This script
loads every record under evidence/ (and optionally extra evidence folders, e.g. the Mac master or a backup) and
reports, per results file, how many rows are backed by a raw record and which ones are not.

  python -I src/evidence_audit.py                       # Colab-era results (M10 Salamandra, M11, M12)
  python -I src/evidence_audit.py --evidence /path/to/master/evidence --files 'results/m1_*.jsonl'

Output: results/evidence_audit.json (counts + ids of unbacked rows). Read-only on evidence/ and results/*.jsonl.
"""
import argparse, glob, json, os

DEFAULT_FILES = ["results/m10_exclusive_salamandra-7b.jsonl", "results/m11_nyt_style_*.jsonl",
                 "results/m12_url_reverse_*.jsonl", "results/rerun_custody*/*.jsonl", "results/m13_most_copied_*.jsonl"]


def load_evidence(dirs):
    shas = {}
    for d in dirs:
        for path in glob.glob(os.path.join(d, "**", "*.jsonl"), recursive=True):
            for line in open(path, encoding="utf-8"):
                if line.strip():
                    rec = json.loads(line)
                    if rec.get("sha256"):
                        shas[rec["sha256"]] = path
    return shas


def row_key(r):
    for k in ("pair_id", "id", "item_id"):
        if k in r:
            return "/".join(str(r[x]) for x in (k, "side", "set", "kind") if x in r)
    return None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--evidence", nargs="*", default=["evidence"])
    ap.add_argument("--files", nargs="*", default=DEFAULT_FILES)
    ap.add_argument("--out", default="results/evidence_audit.json")
    a = ap.parse_args()
    shas = load_evidence(a.evidence)
    report = {"evidence_dirs": a.evidence, "evidence_records": len(shas), "files": {}}
    for pattern in a.files:
        for path in sorted(glob.glob(pattern)):
            rows = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
            field = next((f for f in ("evidence_sha256", "sha256") if rows and f in rows[0]), None)
            if field is None:
                report["files"][path] = {"rows": len(rows), "note": "no evidence hash field"}
                continue
            # a row backed by several records (M13 API: one call per attempt) needs all of them
            backed = lambda h: all(x in shas for x in h) if isinstance(h, list) else h in shas
            missing = [i for i, r in enumerate(rows) if not backed(r.get(field))]
            report["files"][path] = {
                "rows": len(rows), "backed": len(rows) - len(missing), "unbacked": len(missing),
                "unbacked_row_indexes": missing, "unbacked_keys": [row_key(rows[i]) for i in missing]}
            print(f"{path}: {len(rows)} rows, {len(rows) - len(missing)} with raw evidence, {len(missing)} without")
    with open(a.out, "w") as f:
        json.dump(report, f, indent=1)
    print("->", a.out)


if __name__ == "__main__":
    main()
