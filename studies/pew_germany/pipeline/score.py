#!/usr/bin/env python3
"""
score.py — Distribution Accuracy scorer for Study 1C Germany.

Computes DA = 1 − (Σ|real_i − sim_i| / 2) for each question and overall.

Usage:
    python3 score.py --sprint C-1
    python3 score.py --sprint C-13 --verbose
    python3 score.py --compare C-1 C-13       # side-by-side delta

Formula:
    Distribution Accuracy = 1 − (Σ|real_i − sim_i| / 2)
    where real_i and sim_i are the real and simulated proportions for each option.
    Range: 0.0 (worst) to 1.0 (perfect). Human ceiling: 0.91 (Iyengar et al., Stanford).

This is identical to the formula used in Study 1A (US Pew, 88.7%) and Study 1B (India Pew, 85.3%).
"""

import argparse
import json
import sys
from pathlib import Path

HERE       = Path(__file__).resolve().parent
STUDY_ROOT = HERE.parent
QUESTIONS  = STUDY_ROOT / "questions.json"
MANIFESTS  = STUDY_ROOT / "results" / "sprint_manifests"

HUMAN_CEILING = 0.91


def load_questions() -> list[dict]:
    with open(QUESTIONS, encoding="utf-8") as f:
        return json.load(f)


def load_sprint(sprint_id: str) -> dict:
    path = MANIFESTS / f"sprint_{sprint_id}.json"
    if not path.exists():
        print(f"ERROR: Sprint manifest not found: {path}")
        sys.exit(1)
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def da_score(real: dict, sim: dict) -> float:
    """Distribution Accuracy for a single question."""
    all_opts = set(real.keys()) | set(sim.keys())
    total_diff = sum(abs(real.get(o, 0.0) - sim.get(o, 0.0)) for o in all_opts)
    return round(1.0 - total_diff / 2.0, 4)


def score_sprint(sprint_id: str, verbose: bool = False) -> dict[str, float]:
    questions = load_questions()
    manifest  = load_sprint(sprint_id)
    sim_dists = manifest.get("sim_distributions", {})

    scores: dict[str, float] = {}
    for q in questions:
        qid = q["id"]
        real = q["pew_distribution"]
        sim  = sim_dists.get(qid, {})
        scores[qid] = da_score(real, sim)

    scores["overall"] = round(sum(v for k, v in scores.items() if k != "overall") / len(questions), 4)

    if verbose:
        print(f"\nStudy 1C Germany — Sprint {sprint_id} ({manifest.get('model', 'unknown')})")
        print(f"Timestamp: {manifest.get('timestamp', 'N/A')}")
        print("=" * 65)
        for q in questions:
            qid = q["id"]
            sc  = scores[qid]
            gap_to_ceiling = HUMAN_CEILING - sc
            bar_width = int(sc * 30)
            bar = "█" * bar_width + "░" * (30 - bar_width)
            print(f"  {qid} {q['topic']:<35} {bar} {sc:.1%}  (Δ ceiling: {gap_to_ceiling:+.1%})")
        print("-" * 65)
        print(f"  {'OVERALL':<41} {scores['overall']:.1%}  (Δ ceiling: {HUMAN_CEILING - scores['overall']:+.1%})")
        print()

    return scores


def compare_sprints(sprint_a: str, sprint_b: str) -> None:
    questions = load_questions()
    sa = score_sprint(sprint_a)
    sb = score_sprint(sprint_b)

    print(f"\nStudy 1C Germany — Delta: {sprint_a} → {sprint_b}")
    print("=" * 72)
    for q in questions:
        qid = q["id"]
        delta = sb[qid] - sa[qid]
        sign  = "+" if delta >= 0 else ""
        print(f"  {qid} {q['topic']:<35}  {sa[qid]:.1%} → {sb[qid]:.1%}  ({sign}{delta:.1%})")
    print("-" * 72)
    overall_delta = sb["overall"] - sa["overall"]
    sign = "+" if overall_delta >= 0 else ""
    print(f"  {'OVERALL':<41}  {sa['overall']:.1%} → {sb['overall']:.1%}  ({sign}{overall_delta:.1%})")
    print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Study 1C Germany Distribution Accuracy scorer")
    parser.add_argument("--sprint",   help="Sprint ID to score (e.g. C-1)")
    parser.add_argument("--compare",  nargs=2, metavar=("SPRINT_A", "SPRINT_B"),
                        help="Compare two sprints side by side")
    parser.add_argument("--verbose",  action="store_true", help="Show per-question breakdown")
    args = parser.parse_args()

    if args.compare:
        compare_sprints(*args.compare)
    elif args.sprint:
        scores = score_sprint(args.sprint, verbose=True)
        if not args.verbose:
            print(f"Sprint {args.sprint} overall DA: {scores['overall']:.1%}")
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
