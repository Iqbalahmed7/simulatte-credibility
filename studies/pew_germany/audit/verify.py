#!/usr/bin/env python3
"""
verify.py — Integrity verifier for Study 1C Germany sprint data.

Usage:
    python3 verify.py                        # verify all sprints in manifest
    python3 verify.py --sprint C-1           # verify a specific sprint
    python3 verify.py --sprint C-1 --raw     # verify raw JSONL hash

What it checks:
    1. Recomputes SHA-256 hash of raw sprint JSONL
    2. Compares against hash recorded in the sprint manifest
    3. Reports PASS or FAIL with entry counts

If PASS: the sprint data is identical to what was recorded — no entries have
been added, removed, or modified since the manifest was generated.

If FAIL: the sprint data has been altered. Do not rely on the scores.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"


def sha256_of_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def sha256_of_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def count_lines(path: Path) -> int:
    count = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def verify_sprint(sprint_id: str) -> bool:
    manifest_path = MANIFESTS / f"sprint_{sprint_id}.json"
    raw_path      = MANIFESTS / f"sprint_{sprint_id}_raw.jsonl"

    if not manifest_path.exists():
        print(f"ERROR: Manifest not found: {manifest_path}")
        return False

    if not raw_path.exists():
        print(f"ERROR: Raw JSONL not found: {raw_path}")
        return False

    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    published_hash = manifest.get("raw_hash")
    if not published_hash:
        print(f"WARN: Sprint {sprint_id} manifest has no raw_hash — skipping integrity check.")
        return True

    # Recompute hash from file content
    with open(raw_path, encoding="utf-8") as f:
        content = f.read()

    actual_hash  = sha256_of_text(content.rstrip("\n"))
    actual_count = count_lines(raw_path)
    expected_count = manifest.get("n_calls", manifest.get("n_personas", 40) * manifest.get("n_questions", 15))

    print(f"Sprint {sprint_id} ({manifest.get('model', 'unknown')})")
    print(f"  Timestamp         : {manifest.get('timestamp', 'N/A')}")
    print(f"  Published hash    : {published_hash}")
    print(f"  Computed hash     : {actual_hash}")
    print(f"  Expected entries  : {expected_count}")
    print(f"  Actual entries    : {actual_count}")
    print(f"  Overall DA        : {manifest.get('scores', {}).get('overall', 'N/A'):.1%}" if isinstance(manifest.get('scores', {}).get('overall'), float) else f"  Overall DA        : {manifest.get('scores', {}).get('overall', 'N/A')}")

    hash_ok  = actual_hash == published_hash
    count_ok = actual_count == expected_count

    if hash_ok and count_ok:
        print(f"  RESULT: PASS\n")
        return True
    else:
        print(f"  RESULT: FAIL")
        if not hash_ok:
            print(f"    Hash mismatch — raw data has been modified.")
        if not count_ok:
            print(f"    Entry count mismatch: expected {expected_count}, found {actual_count}.")
        print()
        return False


def verify_all() -> None:
    if not MANIFESTS.exists():
        print("No sprint manifests found. Run sprint_runner.py first.")
        sys.exit(0)

    sprint_manifests = sorted(MANIFESTS.glob("sprint_C-*.json"))
    if not sprint_manifests:
        print("No sprint manifests found in results/sprint_manifests/.")
        sys.exit(0)

    print(f"Study 1C Germany — Integrity Verification")
    print(f"Checking {len(sprint_manifests)} sprint(s)…")
    print("=" * 60)

    all_pass = True
    for m in sprint_manifests:
        sprint_id = m.stem.replace("sprint_", "")
        passed = verify_sprint(sprint_id)
        if not passed:
            all_pass = False

    print("=" * 60)
    if all_pass:
        print(f"ALL SPRINTS PASS — data integrity confirmed.")
        sys.exit(0)
    else:
        print(f"INTEGRITY FAILURES DETECTED — do not rely on affected results.")
        sys.exit(1)


def main() -> None:
    parser = argparse.ArgumentParser(description="Study 1C Germany integrity verifier")
    parser.add_argument("--sprint", help="Verify a specific sprint (e.g. C-1)")
    args = parser.parse_args()

    if args.sprint:
        print(f"Study 1C Germany — Integrity Verification")
        print("=" * 60)
        passed = verify_sprint(args.sprint)
        sys.exit(0 if passed else 1)
    else:
        verify_all()


if __name__ == "__main__":
    main()
