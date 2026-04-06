"""
compare_worldview.py — Sprint A-3 before/after comparison.

Compares Study 1A results pre- and post-ARCH-001 worldview layer.
Run after study_1a_pew_replication/run_study.py completes.

Usage:
    python compare_worldview.py
"""

from __future__ import annotations

import json
from pathlib import Path

RESULTS_DIR = Path(__file__).parent / "results"

BEFORE_FILE = RESULTS_DIR / "simulatte_results_pre_worldview.json"
AFTER_FILE  = RESULTS_DIR / "simulatte_results.json"


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def print_comparison() -> None:
    before = load(BEFORE_FILE)
    after  = load(AFTER_FILE)

    b_sum = before["summary"]
    a_sum = after["summary"]

    b_acc = b_sum["mean_distribution_accuracy"]
    a_acc = a_sum["mean_distribution_accuracy"]
    b_mae = b_sum["mean_mae_pct_points"]
    a_mae = a_sum["mean_mae_pct_points"]

    print("\n" + "=" * 70)
    print("STUDY 1A — WORLDVIEW LAYER IMPACT (ARCH-001)")
    print("=" * 70)
    print(f"\n{'Metric':<35} {'Before':>10} {'After':>10} {'Delta':>10}")
    print("-" * 70)
    print(f"{'Mean distribution accuracy':<35} {b_acc:>9.1f}% {a_acc:>9.1f}% {a_acc-b_acc:>+9.1f}pp")
    print(f"{'Mean MAE (pp)':<35} {b_mae:>10.1f} {a_mae:>10.1f} {a_mae-b_mae:>+10.1f}")
    print(f"{'Gap to human benchmark (91%)':<35} {91-b_acc:>9.1f}% {91-a_acc:>9.1f}% {(91-a_acc)-(91-b_acc):>+9.1f}pp")
    print(f"{'Gap to Artificial Societies (86%)':<35} {86-b_acc:>9.1f}% {86-a_acc:>9.1f}% {(86-a_acc)-(86-b_acc):>+9.1f}pp")
    print()

    # Per-question breakdown
    b_qs = {q["question_id"]: q for q in before["questions"]}
    a_qs = {q["question_id"]: q for q in after["questions"]}

    print(f"\n{'Q':>3}  {'Topic':<20} {'Before':>7} {'After':>7} {'Delta':>7}  Collapse fixed?")
    print("-" * 70)

    collapse_fixed = 0
    still_collapsed = 0
    total_questions = 0

    for qid in sorted(b_qs.keys()):
        if qid not in a_qs:
            continue
        bq = b_qs[qid]
        aq = a_qs[qid]
        b_da = bq["distribution_accuracy"]
        a_da = aq["distribution_accuracy"]
        delta = a_da - b_da

        # Check if collapsed before (dominant option > 85%)
        b_max = max(bq["simulated_distribution"].values())
        a_max = max(aq["simulated_distribution"].values())
        was_collapsed = b_max >= 85
        still_col = a_max >= 85
        fixed = was_collapsed and not still_col

        if was_collapsed:
            if fixed:
                collapse_fixed += 1
                status = "✓ FIXED"
            else:
                still_collapsed += 1
                status = "✗ still collapsed"
        else:
            status = "— (wasn't collapsed)"

        total_questions += 1
        print(f"{qid:>3}  {bq['topic']:<20} {b_da:>6.1f}% {a_da:>6.1f}% {delta:>+6.1f}pp  {status}")

    print()
    print(f"Questions that were collapsed (>85% on 1 option) before: {collapse_fixed + still_collapsed}")
    print(f"  Fixed by worldview layer:  {collapse_fixed}")
    print(f"  Still collapsed:           {still_collapsed}")
    print()
    print(f"Overall accuracy: {b_acc:.1f}% → {a_acc:.1f}% ({a_acc-b_acc:+.1f}pp)")
    print(f"Human benchmark:   91.0%  |  Artificial Societies: 86.0%")
    print()

    # Target assessment
    target_low, target_high = 75.0, 85.0
    if a_acc >= target_low:
        print(f"✓ ARCH-001 target achieved: {a_acc:.1f}% (target was {target_low}-{target_high}%)")
    else:
        remaining = target_low - a_acc
        print(f"⚠ ARCH-001 target not yet reached: {a_acc:.1f}% (need +{remaining:.1f}pp to reach {target_low}%)")
    print("=" * 70)


if __name__ == "__main__":
    if not BEFORE_FILE.exists():
        print(f"ERROR: Before file not found: {BEFORE_FILE}")
    elif not AFTER_FILE.exists():
        print(f"ERROR: After file not found: {AFTER_FILE}")
        print("Run: python run_study.py --simulatte-only --cohort-size 50")
    else:
        print_comparison()
