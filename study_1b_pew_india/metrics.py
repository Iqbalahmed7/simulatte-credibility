"""
metrics.py — Distribution accuracy and MAE calculation for Study 1B (India).

Metrics used (same as Artificial Societies Jan 2026 white paper):
  - Distribution Accuracy: 1 - (sum of absolute differences / 2)
    e.g. Real: {A:70%, B:30%}, Simulated: {A:60%, B:40%}
    => |70-60| + |30-40| = 20 => accuracy = 1 - 20/200 = 90%

  - Mean Absolute Error (MAE): average absolute difference in % points
    across all options for a question.

  - Human Benchmark ceiling: 91% (Stanford finding — individuals change
    answers ~19% of the time when asked the same question again).

Identical to study_1a/metrics.py — shared implementation for comparability.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class QuestionResult:
    question_id: str
    question_text: str
    topic: str
    system: str
    pew_distribution: dict[str, float]
    sim_distribution: dict[str, float]
    distribution_accuracy: float
    mae: float
    n_responses: int
    n_parseable: int
    raw_responses: list[str] = field(default_factory=list)


@dataclass
class StudyResult:
    system: str
    questions: list[QuestionResult] = field(default_factory=list)

    @property
    def mean_distribution_accuracy(self) -> float:
        if not self.questions:
            return 0.0
        return sum(q.distribution_accuracy for q in self.questions) / len(self.questions)

    @property
    def mean_mae(self) -> float:
        if not self.questions:
            return 0.0
        return sum(q.mae for q in self.questions) / len(self.questions)

    @property
    def gap_to_human_benchmark(self) -> float:
        return 0.91 - self.mean_distribution_accuracy

    def summary(self) -> dict:
        return {
            "system": self.system,
            "n_questions": len(self.questions),
            "mean_distribution_accuracy": round(self.mean_distribution_accuracy * 100, 1),
            "mean_mae_pct_points": round(self.mean_mae, 1),
            "gap_to_human_benchmark_pct_points": round(self.gap_to_human_benchmark * 100, 1),
            "human_benchmark": 91.0,
        }


def compute_distribution_accuracy(
    real: dict[str, float],
    simulated: dict[str, float],
) -> float:
    """
    Distribution accuracy = 1 - (sum of |real_i - sim_i|) / 2

    The /2 normalises total variation distance (max=2) to a 0-1 scale.
    """
    all_keys = set(real.keys()) | set(simulated.keys())
    total_abs_diff = sum(
        abs(real.get(k, 0.0) - simulated.get(k, 0.0))
        for k in all_keys
    )
    return 1.0 - (total_abs_diff / 2.0)


def compute_mae(
    real: dict[str, float],
    simulated: dict[str, float],
) -> float:
    """Mean Absolute Error in percentage points across all options."""
    all_keys = set(real.keys()) | set(simulated.keys())
    abs_diffs = [
        abs(real.get(k, 0.0) - simulated.get(k, 0.0)) * 100
        for k in all_keys
    ]
    return sum(abs_diffs) / len(abs_diffs) if abs_diffs else 0.0


def responses_to_distribution(
    responses: list[str],
    valid_options: list[str],
    option_texts: dict[str, str] | None = None,
) -> tuple[dict[str, float], int]:
    """
    Convert raw response strings to a proportional distribution.

    Parsing strategy (priority order):
      1. Single letter exactly matching a valid option
      2. Starts with "LETTER —" / "LETTER." / "LETTER)" / "LETTER:"
      2b. Starts with option text (e.g. "Somewhat unfavorable — ...") [Sprint A-2]
      3. Explicit declaration: "going with X", "choose X", "answer is X"
      4. First word stripped of punctuation
      5. No greedy fallback

    Args:
        responses: Raw response strings from the survey model.
        valid_options: List of valid option letters, e.g. ["A", "B", "C", "D"].
        option_texts: Optional mapping of letter → option text, e.g.
            {"A": "Very favorable", "B": "Somewhat favorable", ...}.
            When provided, enables rule 2b to recover responses that start
            with the full option text rather than a letter (in04 parse failure
            pattern: "Somewhat unfavorable — [explanation]").

    Returns:
        (distribution dict, n_parseable)
    """
    counts: dict[str, int] = {opt: 0 for opt in valid_options}
    n_parseable = 0

    for response in responses:
        parsed = _parse_response(response, valid_options, option_texts)
        if parsed:
            counts[parsed] += 1
            n_parseable += 1

    if n_parseable == 0:
        return {opt: 0.0 for opt in valid_options}, 0

    distribution = {opt: counts[opt] / n_parseable for opt in valid_options}
    return distribution, n_parseable


def _parse_response(
    response: str,
    valid_options: list[str],
    option_texts: dict[str, str] | None = None,
) -> str | None:
    import re

    if not response:
        return None

    text = response.strip()
    text_upper = text.upper()
    valid_set = set(valid_options)

    # 1. Single letter
    if len(text) == 1 and text.upper() in valid_set:
        return text.upper()

    # 2. Starts with "LETTER —" or "LETTER." or "LETTER)" or "LETTER:"
    for opt in valid_options:
        for pattern in [f"{opt} —", f"{opt}—", f"{opt}.", f"{opt})", f"{opt}:"]:
            if text_upper.startswith(pattern.upper()):
                return opt

    # 2b. Starts with option text (Sprint A-2 fix for in04 parse failure).
    # Handles responses like "Somewhat unfavorable — [explanation]" where the
    # survey model writes the option text rather than a letter prefix.
    if option_texts:
        text_lower = text.lower()
        # Sort by length descending to match longest prefix first
        # (avoids "Very favorable" being matched by "favorable" substring).
        for opt_letter, opt_text in sorted(
            option_texts.items(), key=lambda kv: len(kv[1]), reverse=True
        ):
            if opt_letter in valid_set and text_lower.startswith(opt_text.lower()):
                return opt_letter

    # 3. Explicit declaration patterns
    declaration_patterns = [
        r"(?:I'?M\s+)?GOING\s+WITH\s+([A-Z])",
        r"I\s+CHOOSE\s+([A-Z])",
        r"I\s+SELECT\s+([A-Z])",
        r"MY\s+ANSWER\s+IS\s+([A-Z])",
        r"ANSWER\s+IS\s+([A-Z])",
        r"ANSWER:\s*([A-Z])",
        r"I\s+WOULD\s+SAY\s+([A-Z])",
        r"I\s+PICK\s+([A-Z])",
        r"I\s+GO\s+WITH\s+([A-Z])",
    ]
    for pattern in declaration_patterns:
        match = re.search(pattern, text_upper)
        if match:
            letter = match.group(1)
            if letter in valid_set:
                return letter

    # 4. First word stripped of punctuation
    first_word = text.split()[0].upper().strip(".,():;—-")
    if first_word in valid_set:
        return first_word

    return None


def evaluate_system(
    system_name: str,
    questions: list[dict],
    raw_survey_output: dict[str, list[str]],
) -> StudyResult:
    """
    Evaluate a system's survey responses against Pew India ground truth.
    """
    result = StudyResult(system=system_name)

    for q in questions:
        qid = q["id"]
        responses = raw_survey_output.get(qid, [])
        valid_options = list(q["options"].keys())
        option_texts = {k: v for k, v in q["options"].items()}

        # Ground truth — exclude DK/Refused, renormalise
        raw_pew = {k: v for k, v in q["pew_distribution"].items() if k != "DK"}
        total = sum(raw_pew.values())
        pew_dist = {k: v / total for k, v in raw_pew.items()}

        sim_dist, n_parseable = responses_to_distribution(responses, valid_options, option_texts)

        acc = compute_distribution_accuracy(pew_dist, sim_dist)
        mae = compute_mae(pew_dist, sim_dist)

        result.questions.append(QuestionResult(
            question_id=qid,
            question_text=q["text"],
            topic=q["topic"],
            system=system_name,
            pew_distribution=pew_dist,
            sim_distribution=sim_dist,
            distribution_accuracy=acc,
            mae=mae,
            n_responses=len(responses),
            n_parseable=n_parseable,
            raw_responses=responses[:5],
        ))

    return result


def print_comparison_table(results: list[StudyResult]) -> None:
    """Print a formatted comparison table to stdout."""
    HUMAN_BENCHMARK = 91.0
    STUDY_1A_RESULT = 86.1  # Simulatte B-8 on US Pew data

    print("\n" + "=" * 72)
    print("STUDY 1B: PEW INDIA REPLICATION — DISTRIBUTION ACCURACY RESULTS")
    print("=" * 72)
    print(f"{'System':<22} {'Dist. Accuracy':>16} {'MAE (pp)':>10} {'Gap to Benchmark':>18}")
    print("-" * 72)

    for r in sorted(results, key=lambda x: x.mean_distribution_accuracy, reverse=True):
        acc = r.mean_distribution_accuracy * 100
        gap = HUMAN_BENCHMARK - acc
        print(f"{r.system:<22} {acc:>15.1f}%  {r.mean_mae:>9.1f}  {gap:>+17.1f} pp")

    print("-" * 72)
    print(f"{'Human Benchmark (ceiling)':<22} {HUMAN_BENCHMARK:>15.1f}%  {'—':>9}  {'0.0 pp':>18}")
    print(f"{'Simulatte Study 1A (US)':<22} {STUDY_1A_RESULT:>15.1f}%  {'—':>9}  {HUMAN_BENCHMARK - STUDY_1A_RESULT:>+17.1f} pp")
    print("=" * 72)
    print("  Study 1A reference: US Pew replication, Sprint B-8, 60 personas, 15 questions.")
    print(f"  Human benchmark = 91% (Stanford: ~19% self-inconsistency rate).")


def save_results(results: list[StudyResult], output_dir: Path) -> None:
    """Save results to JSON files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    for r in results:
        out = {
            "summary": r.summary(),
            "questions": [
                {
                    "question_id": q.question_id,
                    "topic": q.topic,
                    "question_text": q.question_text,
                    "distribution_accuracy": round(q.distribution_accuracy * 100, 1),
                    "mae_pct_points": round(q.mae, 1),
                    "n_responses": q.n_responses,
                    "n_parseable": q.n_parseable,
                    "pew_distribution": {k: round(v * 100, 1) for k, v in q.pew_distribution.items()},
                    "simulated_distribution": {k: round(v * 100, 1) for k, v in q.sim_distribution.items()},
                    "sample_responses": q.raw_responses,
                }
                for q in r.questions
            ]
        }
        fname = output_dir / f"{r.system.replace(' ', '_').lower()}_results.json"
        fname.write_text(json.dumps(out, indent=2))
        print(f"  Saved: {fname}")

    combined = {
        "study": "1B — Pew India Replication",
        "human_benchmark_pct": 91.0,
        "study_1a_simulatte_pct": 86.1,
        "systems": [r.summary() for r in results],
    }
    combined_path = output_dir / "comparison.json"
    combined_path.write_text(json.dumps(combined, indent=2))
    print(f"  Saved: {combined_path}")
