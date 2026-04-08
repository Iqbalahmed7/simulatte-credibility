#!/usr/bin/env python3
"""
verify.py — Public integrity verifier for the Simulatte LLM Comparison audit.

Usage:
    python3 verify.py

What it checks:
    1. Recomputes the SHA-256 root hash of stripped_audit.jsonl
    2. Compares it against the published root_hash in audit_manifest.json
    3. Reports PASS or FAIL with entry counts

If PASS: the audit file is identical to what was published — no entries have
been added, removed, or modified since the manifest was generated.

If FAIL: the file has been altered. Do not rely on the results.
"""

import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
STRIPPED_AUDIT = HERE / "stripped_audit.jsonl"
MANIFEST       = HERE / "audit_manifest.json"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def count_lines(path: Path) -> int:
    count = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def main() -> None:
    if not STRIPPED_AUDIT.exists():
        print("ERROR: stripped_audit.jsonl not found.")
        sys.exit(1)
    if not MANIFEST.exists():
        print("ERROR: audit_manifest.json not found.")
        sys.exit(1)

    with MANIFEST.open(encoding="utf-8") as f:
        manifest = json.load(f)

    published_hash  = manifest["root_hash"]
    published_count = manifest["total_entries"]
    run_ids         = manifest["run_ids"]

    print("Simulatte LLM Comparison — Audit Integrity Check")
    print("=" * 54)
    print(f"Study:          {manifest['study']}")
    print(f"Generated at:   {manifest['generated_at']}")
    print(f"Run IDs:")
    for rid, count in run_ids.items():
        print(f"  {rid}  ({count} entries)")
    print(f"Models covered: {len(manifest['models_covered'])}")
    print()

    print("Checking …")
    actual_hash  = sha256_of_file(STRIPPED_AUDIT)
    actual_count = count_lines(STRIPPED_AUDIT)

    print(f"  Published root hash : {published_hash}")
    print(f"  Computed root hash  : {actual_hash}")
    print(f"  Published entries   : {published_count}")
    print(f"  Actual entries      : {actual_count}")
    print()

    hash_ok  = actual_hash  == published_hash
    count_ok = actual_count == published_count

    if hash_ok and count_ok:
        print("RESULT: PASS — audit file is intact and unmodified.")
        sys.exit(0)
    else:
        print("RESULT: FAIL — audit file does not match the published manifest.")
        if not hash_ok:
            print("  Root hash mismatch: file contents have changed.")
        if not count_ok:
            print(f"  Entry count mismatch: expected {published_count}, found {actual_count}.")
        sys.exit(1)


if __name__ == "__main__":
    main()
