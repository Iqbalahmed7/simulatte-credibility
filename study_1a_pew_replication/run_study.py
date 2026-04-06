"""
run_study.py — Orchestrator for Study 1A: Pew Replication.

Usage:
  # Full run (all systems, all questions):
  python run_study.py

  # Quick test (3 questions, 5 personas):
  python run_study.py --quick

  # Simulatte only (skip LLM baselines):
  python run_study.py --simulatte-only

  # Use existing Simulatte cohort (skip generation):
  python run_study.py --cohort-id <cohort_id>

  # Specify number of personas:
  python run_study.py --cohort-size 50

  # Run LLM baselines only (no Simulatte):
  python run_study.py --baselines-only

Output:
  results/simulatte_results.json
  results/claude_baseline_results.json
  results/gpt4o_baseline_results.json
  results/comparison.json        ← main output for publication
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Setup path so we can import from this directory
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from metrics import StudyResult, evaluate_system, print_comparison_table, save_results
from simulatte_runner import run_simulatte_study
from llm_baseline import run_claude_baseline, run_gpt4o_baseline

RESULTS_DIR = Path(__file__).parent / "results"
QUESTIONS_PATH = Path(__file__).parent / "data" / "questions.json"


def load_questions(quick: bool = False) -> list[dict]:
    """Load questions from data/questions.json."""
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
    """Run Simulatte survey and return (cohort_id, StudyResult)."""
    print("\n" + "=" * 60)
    print("SIMULATTE")
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


async def run_baselines(
    questions: list[dict],
    n_personas: int,
) -> list[StudyResult]:
    """Run Claude and GPT-4o baselines."""
    print("\n" + "=" * 60)
    print("LLM BASELINES")
    print("=" * 60)

    results = []

    # Claude baseline
    print("\n--- Claude Sonnet (simple persona) ---")
    claude_responses = await run_claude_baseline(questions, n_personas=n_personas)
    claude_result = evaluate_system("Claude Sonnet (baseline)", questions, claude_responses)
    print(f"  → Mean distribution accuracy: {claude_result.mean_distribution_accuracy * 100:.1f}%")
    results.append(claude_result)

    # GPT-4o baseline
    print("\n--- GPT-4o (simple persona) ---")
    gpt_responses = await run_gpt4o_baseline(questions, n_personas=n_personas)
    if any(gpt_responses.values()):
        gpt_result = evaluate_system("GPT-4o (baseline)", questions, gpt_responses)
        print(f"  → Mean distribution accuracy: {gpt_result.mean_distribution_accuracy * 100:.1f}%")
        results.append(gpt_result)
    else:
        print("  GPT-4o skipped (no responses).")

    return results


def print_study_header(questions: list[dict], cohort_size: int) -> None:
    print("\n" + "=" * 60)
    print("STUDY 1A: PEW REPLICATION STUDY")
    print("Simulatte Credibility Research Program")
    print("=" * 60)
    print(f"  Questions:      {len(questions)}")
    print(f"  Cohort size:    {cohort_size} personas")
    print(f"  Human ceiling:  91% (Stanford self-inconsistency baseline)")
    print(f"  Competitor ref: 86% (Artificial Societies, Jan 2026)")
    print()


def main():
    parser = argparse.ArgumentParser(description="Study 1A: Pew Replication")
    parser.add_argument("--quick", action="store_true",
                        help="Quick test: 3 questions, 5 personas")
    parser.add_argument("--simulatte-only", action="store_true",
                        help="Run Simulatte only, skip LLM baselines")
    parser.add_argument("--baselines-only", action="store_true",
                        help="Run LLM baselines only, skip Simulatte")
    parser.add_argument("--cohort-id", type=str, default=None,
                        help="Reuse existing cohort ID(s), comma-separated for multiple")
    parser.add_argument("--cohort-ids", type=str, default=None,
                        help="Alias for --cohort-id, comma-separated list of cohort IDs")
    parser.add_argument("--cohort-size", type=int, default=30,
                        help="Number of personas in Simulatte cohort (default: 30)")
    args = parser.parse_args()

    if args.quick:
        cohort_size = 5
        n_personas = 5
    else:
        cohort_size = args.cohort_size
        n_personas = args.cohort_size  # Match cohort size for fair comparison

    questions = load_questions(quick=args.quick)
    print_study_header(questions, cohort_size)

    all_results: list[StudyResult] = []

    # --- Simulatte ---
    if not args.baselines_only:
        # Support multiple pre-generated cohort IDs (comma-separated)
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

    # --- LLM Baselines ---
    if not args.simulatte_only:
        baseline_results = asyncio.run(run_baselines(questions, n_personas=n_personas))
        all_results.extend(baseline_results)

    # --- Output ---
    if all_results:
        print_comparison_table(all_results)
        save_results(all_results, RESULTS_DIR)
        print(f"\n  Results saved to: {RESULTS_DIR}/")
    else:
        print("\nNo results to report — nothing was run.")

    # --- Notes ---
    print("\n" + "=" * 60)
    print("NOTES & LIMITATIONS")
    print("=" * 60)
    print("""
  1. DEMOGRAPHIC MATCHING: Using 'us_general' domain pool — 34 profiles
     approximating US Census / Pew ATP composition across age, gender,
     race, education, region, and income. Pool defined in:
     /Persona Generator/src/generation/demographic_sampler.py

  2. QUESTION FORMATTING: Questions are formatted to force single-letter
     responses. Parse rate < 100% indicates some personas are not following
     the instruction — monitor n_parseable vs n_responses per question.

  3. SAMPLE SIZE: For a publishable result, run with --cohort-size 200+.
     Current default (30) is proof-of-concept only.

  4. PEW DISTRIBUTIONS: The distributions in data/questions.json are sourced
     from Pew Research Center published reports. For highest accuracy,
     replace with actual microdata distributions (requires Pew account).
     See: https://www.pewresearch.org/american-trends-panel-datasets/
    """)


if __name__ == "__main__":
    main()
