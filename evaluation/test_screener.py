import json
import sys
import time
import pytest
from pathlib import Path

# Ensure project root is on sys.path when running as a script (pytest adds it automatically)
sys.path.insert(0, str(Path(__file__).parent.parent))

from matching.agent import run_match

CASES = json.loads(
    (Path(__file__).parent.parent / "data/test_cases/cases.json").read_text()
)


def _get_matched_ids(result: dict, threshold: float = 0.5) -> set[str]:
    return {m["trial_id"] for m in result["matches"] if m["score"] >= threshold}


# --- Hallucination tests (deterministic — must never fail) ---

@pytest.mark.parametrize("case", [c for c in CASES if not c["should_match"]])
def test_no_hallucinated_matches(case):
    """Disqualified patients must never receive a high-confidence match."""
    result = run_match(case["note"])
    matched = _get_matched_ids(result, threshold=0.5)
    assert matched == set(), (
        f"[{case['id']}] Hallucinated matches for disqualified patient: {matched}\n"
        f"Note: {case['note']}\nNotes: {case['notes']}"
    )


# --- Precision / Recall (run separately — prints aggregate metrics) ---

def compute_metrics(threshold: float = 0.5) -> dict:
    true_positives = 0
    false_positives = 0
    false_negatives = 0

    for case in CASES:
        result = run_match(case["note"])
        predicted = _get_matched_ids(result, threshold)
        correct = set(case["correct_trial_ids"])

        true_positives += len(predicted & correct)
        false_positives += len(predicted - correct)
        false_negatives += len(correct - predicted)

    precision = (
        true_positives / (true_positives + false_positives)
        if (true_positives + false_positives) > 0 else 0.0
    )
    recall = (
        true_positives / (true_positives + false_negatives)
        if (true_positives + false_negatives) > 0 else 0.0
    )

    return {
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "true_positives": true_positives,
        "false_positives": false_positives,
        "false_negatives": false_negatives,
    }


if __name__ == "__main__":
    print("Running evaluation across all 20 test cases...")
    print("(This will make ~80 Groq API calls — takes 3-5 minutes)\n")
    metrics = compute_metrics()
    print("=== EVALUATION RESULTS ===")
    print(f"Precision:        {metrics['precision']:.1%}")
    print(f"Recall:           {metrics['recall']:.1%}")
    print(f"True Positives:   {metrics['true_positives']}")
    print(f"False Positives:  {metrics['false_positives']}")
    print(f"False Negatives:  {metrics['false_negatives']}")
    print("\nTarget: Precision > 85%, Recall > 80%")
