"""
metrics.py — Distribution accuracy and MAE calculation for Study 1A.

Metrics used (same as Artificial Societies Jan 2026 white paper):
  - Distribution Accuracy: 1 - (sum of absolute differences / 2)
    e.g. Real: {A:70%, B:30%}, Simulated: {A:60%, B:40%}
    => |70-60| + |30-40| = 20 => accuracy = 1 - 20/200 = 90%

  - Mean Absolute Error (MAE): average absolute difference in % points
    across all options for a question.

  - Human Benchmark ceiling: 91% (Stanford finding — individuals change
    answers ~19% of the time when asked the same question again).
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
    system: str                        # "simulatte", "gpt4o", "claude", etc.
    pew_distribution: dict[str, float] # ground truth {option: proportion}
    sim_distribution: dict[str, float] # simulated {option: proportion}
    distribution_accuracy: float       # 0-1
    mae: float                         # mean absolute error in % points
    n_responses: int                   # number of simulated responses
    n_parseable: int                   # responses successfully parsed to an option
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
        """Points below the 91% human benchmark ceiling."""
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
    Compute distribution accuracy following Artificial Societies methodology.

    Distribution accuracy = 1 - (sum of |real_i - sim_i|) / 2

    The /2 normalises the total variation distance (which sums to 2 at maximum
    disagreement) to a 0-1 scale.

    Args:
        real: Ground truth proportions, should sum to ~1.0. Keys are option letters.
        simulated: Simulated proportions. Keys must match real.

    Returns:
        Float between 0 and 1. Higher is better.
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
    """
    Compute Mean Absolute Error in percentage points across all options.

    Args:
        real: Ground truth proportions.
        simulated: Simulated proportions.

    Returns:
        MAE in percentage points (0-100 scale).
    """
    all_keys = set(real.keys()) | set(simulated.keys())
    abs_diffs = [
        abs(real.get(k, 0.0) - simulated.get(k, 0.0)) * 100
        for k in all_keys
    ]
    return sum(abs_diffs) / len(abs_diffs) if abs_diffs else 0.0


def responses_to_distribution(
    responses: list[str],
    valid_options: list[str],
) -> tuple[dict[str, float], int]:
    """
    Convert a list of raw response strings to a proportional distribution.

    Parsing strategy:
      1. Strip and upper-case the response.
      2. If response is exactly one letter matching a valid option — use it.
      3. Otherwise check if any valid option letter appears in the response.
      4. If the full option text appears in the response, map to that option.
      5. Unparseable responses are excluded from the distribution.

    Args:
        responses: List of raw decision strings from the survey.
        valid_options: List of valid option keys, e.g. ["A", "B", "C"].

    Returns:
        Tuple of (distribution dict, n_parseable).
        Distribution values sum to 1.0 (excluding unparseable).
    """
    counts: dict[str, int] = {opt: 0 for opt in valid_options}
    n_parseable = 0

    for response in responses:
        parsed = _parse_response(response, valid_options)
        if parsed:
            counts[parsed] += 1
            n_parseable += 1

    if n_parseable == 0:
        return {opt: 0.0 for opt in valid_options}, 0

    distribution = {opt: counts[opt] / n_parseable for opt in valid_options}
    return distribution, n_parseable


def _parse_response(response: str, valid_options: list[str]) -> str | None:
    """
    Parse a single response string to a valid option letter.

    Simulatte personas give verbose reasoning answers like:
      "I'm going with C — Only fair. The economy..."
      "C — Only fair. It's not a..."
      "I choose A — more strict."

    Priority order:
      1. Response is a single letter (ideal forced-choice output)
      2. Response starts with "LETTER —" or "LETTER." or "LETTER)"
      3. Explicit declaration: "going with X", "choose X", "select X", "answer is X"
      4. Letter in first word (stripped of punctuation)
      5. NO fallback to first-letter-found in body text (too error-prone for verbose responses)
    """
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

    # 3. Explicit declaration patterns (verbose reasoning style)
    # Search case-insensitively in the original text for "LETTER" captures
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

    # 5. No greedy fallback — return None for unparseable verbose responses
    return None


def evaluate_system(
    system_name: str,
    questions: list[dict],
    raw_survey_output: dict[str, list[str]],
) -> StudyResult:
    """
    Evaluate a system's survey responses against Pew ground truth.

    Args:
        system_name: Label for this system (e.g. "simulatte", "gpt4o").
        questions: List of question dicts from questions.json.
        raw_survey_output: Dict mapping question_id -> list of raw response strings.

    Returns:
        StudyResult with per-question and aggregate metrics.
    """
    result = StudyResult(system=system_name)

    for q in questions:
        qid = q["id"]
        responses = raw_survey_output.get(qid, [])
        valid_options = [k for k in q["options"].keys()]

        # Ground truth — exclude DK/Refused, renormalise
        raw_pew = {k: v for k, v in q["pew_distribution"].items() if k != "DK"}
        total = sum(raw_pew.values())
        pew_dist = {k: v / total for k, v in raw_pew.items()}

        sim_dist, n_parseable = responses_to_distribution(responses, valid_options)

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
            raw_responses=responses[:5],  # store first 5 for inspection
        ))

    return result


def print_comparison_table(results: list[StudyResult]) -> None:
    """Print a formatted comparison table to stdout."""
    HUMAN_BENCHMARK = 91.0
    ARTIFICIAL_SOCIETIES = 86.0

    print("\n" + "=" * 72)
    print("STUDY 1A: PEW REPLICATION — DISTRIBUTION ACCURACY RESULTS")
    print("=" * 72)
    print(f"{'System':<22} {'Dist. Accuracy':>16} {'MAE (pp)':>10} {'Gap to Benchmark':>18}")
    print("-" * 72)

    for r in sorted(results, key=lambda x: x.mean_distribution_accuracy, reverse=True):
        acc = r.mean_distribution_accuracy * 100
        gap = HUMAN_BENCHMARK - acc
        print(f"{r.system:<22} {acc:>15.1f}%  {r.mean_mae:>9.1f}  {gap:>+17.1f} pp")

    print("-" * 72)
    print(f"{'Human Benchmark (ceiling)':<22} {HUMAN_BENCHMARK:>15.1f}%  {'—':>9}  {'0.0 pp':>18}")
    print(f"{'Artificial Societies*':<22} {ARTIFICIAL_SOCIETIES:>15.1f}%  {'—':>9}  {HUMAN_BENCHMARK - ARTIFICIAL_SOCIETIES:>+17.1f} pp")
    print("=" * 72)
    print("* Self-reported, Jan 2026 white paper. 1,000 UC Berkeley surveys.")
    print(f"  Human benchmark = 91% (Stanford: individuals change answers ~19%")
    print(f"  of the time when re-asked the same question).")


def save_results(results: list[StudyResult], output_dir: Path) -> None:
    """Save results to JSON files in output_dir."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Per-system files
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

    # Combined comparison file
    combined = {
        "study": "1A — Pew Replication",
        "human_benchmark_pct": 91.0,
        "artificial_societies_benchmark_pct": 86.0,
        "systems": [r.summary() for r in results],
    }
    combined_path = output_dir / "comparison.json"
    combined_path.write_text(json.dumps(combined, indent=2))
    print(f"  Saved: {combined_path}")
