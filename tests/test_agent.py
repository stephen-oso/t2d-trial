from matching.agent import run_match


def test_run_match_returns_structure():
    note = (
        "52-year-old female, Type 2 Diabetes 18 months ago. "
        "HbA1c 8.2%, BMI 29.4, eGFR 85. Metformin 500mg. No insulin."
    )
    result = run_match(note)
    assert "patient" in result
    assert "matches" in result
    assert isinstance(result["matches"], list)
    if result["matches"]:
        match = result["matches"][0]
        assert "trial_id" in match
        assert "score" in match
        assert "criteria" in match
        assert "missing_info" in match


def test_insulin_patient_gets_low_scores():
    note = (
        "65-year-old male, T2D for 10 years, HbA1c 9.1%. "
        "On insulin glargine 20 units nightly."
    )
    result = run_match(note)
    # All 10 trials exclude insulin users — no match should score > 0.5
    high_scores = [m for m in result["matches"] if m["score"] > 0.5]
    assert len(high_scores) == 0, f"Unexpected high-scoring matches: {high_scores}"
