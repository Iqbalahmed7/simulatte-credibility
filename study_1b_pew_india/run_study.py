"""
run_study.py — Orchestrator for Study 1B: Pew India Replication.

Usage:
  # Full run (Simulatte only, 40 personas):
  python run_study.py --simulatte-only

  # Quick test (3 questions, 5 personas):
  python run_study.py --quick

  # Specify cohort size:
  python run_study.py --simulatte-only --cohort-size 60

  # Reuse existing cohort (skip generation):
  python run_study.py --cohort-id <cohort_id>

  # Multiple pre-generated cohorts (comma-separated):
  python run_study.py --cohort-ids <id1>,<id2>,<id3>

Output:
  results/simulatte_results.json
  results/comparison.json
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from metrics import StudyResult, evaluate_system, print_comparison_table, save_results
from simulatte_runner import run_simulatte_study

RESULTS_DIR = Path(__file__).parent / "results"
QUESTIONS_PATH = Path(__file__).parent / "data" / "questions_india.json"


def load_questions(quick: bool = False) -> list[dict]:
    questions = json.loads(QUESTIONS_PATH.read_text())
    if quick:
        questions = questions[:3]
        print(f"[Quick mode] Using {len(questions)} questions.")
    else:
        print(f"[Full mode] Using {len(questions)} questions.")
    return questions


def run_simulatte(
    questions: list[dict],
    cohort_size: int,
    cohort_id: str | None,
    cohort_ids: list[str] | None = None,
) -> tuple[str, StudyResult]:
    print("\n" + "=" * 60)
    print("SIMULATTE — INDIA")
    print("=" * 60)

    used_cohort_id, raw_responses = run_simulatte_study(
        questions=questions,
        cohort_size=cohort_size,
        existing_cohort_id=cohort_id,
        existing_cohort_ids=cohort_ids,
    )

    result = evaluate_system("Simulatte", questions, raw_responses)
    print(f"\n  → Mean distribution accuracy: {result.mean_distribution_accuracy * 100:.1f}%")
    print(f"  → Mean MAE: {result.mean_mae:.1f} pp")
    return used_cohort_id, result


def print_study_header(questions: list[dict], cohort_size: int) -> None:
    print("\n" + "=" * 60)
    print("STUDY 1B: PEW INDIA REPLICATION")
    print("Simulatte Credibility Research Program")
    print("=" * 60)
    print(f"  Questions:      {len(questions)}")
    print(f"  Cohort size:    {cohort_size} personas")
    print(f"  Domain:         india_general (BJP/opposition lean, religion, caste, region)")
    print(f"  Human ceiling:  91% (Stanford self-inconsistency baseline)")
    print(f"  Study 1A ref:   86.1% (US Pew, Sprint B-8, 60 personas)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Study 1B: Pew India Replication")
    parser.add_argument("--quick", action="store_true",
                        help="Quick test: 3 questions, 5 personas")
    parser.add_argument("--simulatte-only", action="store_true",
                        help="Run Simulatte only (recommended — no LLM baselines for 1B yet)")
    parser.add_argument("--cohort-id", type=str, default=None,
                        help="Reuse existing cohort ID")
    parser.add_argument("--cohort-ids", type=str, default=None,
                        help="Comma-separated list of pre-generated cohort IDs")
    parser.add_argument("--cohort-size", type=int, default=40,
                        help="Number of personas in cohort (default: 40)")
    args = parser.parse_args()

    if args.quick:
        cohort_size = 5
    else:
        cohort_size = args.cohort_size

    questions = load_questions(quick=args.quick)
    print_study_header(questions, cohort_size)

    all_results: list[StudyResult] = []

    # Parse cohort IDs
    raw_ids = args.cohort_ids or args.cohort_id
    if raw_ids:
        cohort_id_list = [c.strip() for c in raw_ids.split(",") if c.strip()]
    else:
        cohort_id_list = None

    used_cohort_id, sim_result = run_simulatte(
        questions=questions,
        cohort_size=cohort_size,
        cohort_id=cohort_id_list[0] if cohort_id_list and len(cohort_id_list) == 1 else None,
        cohort_ids=cohort_id_list if cohort_id_list and len(cohort_id_list) > 1 else None,
    )
    all_results.append(sim_result)
    print(f"\n  Simulatte cohort ID: {used_cohort_id}")
    print(f"  (reuse with --cohort-id {used_cohort_id})")

    if all_results:
        print_comparison_table(all_results)
        save_results(all_results, RESULTS_DIR)
        print(f"\n  Results saved to: {RESULTS_DIR}/")

    print("\n" + "=" * 60)
    print("NOTES & LIMITATIONS")
    print("=" * 60)
    print("""
  1. DEMOGRAPHIC MATCHING: Using 'india_general' domain pool — 40 profiles
     approximating Pew India survey composition across religion (Hindu/Muslim/
     Sikh/Christian), caste (General/OBC/SC/ST), region (North/South/West/East),
     urban tier, income, education, and BJP/opposition political lean.
     Pool defined in:
     /Persona Generator/src/generation/demographic_sampler.py

  2. QUESTION FORMATTING: Questions force single-letter responses. Parse rate
     < 100% indicates some personas are not following the instruction.

  3. SAMPLE SIZE: For publication, run with --cohort-size 200+.
     Default (40) matches the india_general pool size for proof-of-concept.

  4. PEW DISTRIBUTIONS: Sourced from Pew India reports:
     - Global Attitudes Spring 2023 (N=2,611) — political questions
     - Religion in India 2021 (N=29,999) — religion/tolerance questions
     - Gender Roles in India 2022 (N=29,999) — gender norms questions
     - Global Attitudes Spring 2017/2018 — economic/government trust questions
    """)


if __name__ == "__main__":
    main()
