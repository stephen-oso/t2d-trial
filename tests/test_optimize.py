from unittest.mock import MagicMock, patch
from extraction.optimize import optimize_note


def _mock_response(text: str):
    msg = MagicMock()
    msg.content = [MagicMock(text=text)]
    return msg


def test_optimize_note_returns_structure():
    optimized = (
        "S: 48-year-old male, T2D 4 years.\n\n"
        "O: HbA1c 7.6%, Fasting Plasma Glucose (FPG): [not found — add if available], "
        "OGTT 2-hour glucose: [not found — add if available], BMI 27.1, eGFR 91 mL/min, "
        "AST: [not found — add if available], ALT: [not found — add if available], "
        "ALP: [not found — add if available], Total Bilirubin: [not found — add if available]. "
        "Metformin 500mg BID.\n\nA: T2DM near target.\n\nP: Continue current regimen."
    )
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(optimized)
        result = optimize_note("Patient has diabetes. HbA1c 7.6%. On metformin.")

    assert "optimized_note" in result
    assert "missing_fields" in result
    assert isinstance(result["optimized_note"], str)
    assert isinstance(result["missing_fields"], list)
    assert "FPG" in result["missing_fields"]
    assert "OGTT" in result["missing_fields"]


def test_optimize_note_no_missing_fields():
    full_note = (
        "S: 48M, T2D 4 years.\n\n"
        "O: HbA1c 7.6%, FPG 148 mg/dL, OGTT 2-hour glucose 218 mg/dL, BMI 27.1, "
        "eGFR 91 mL/min, AST 22 U/L, ALT 28 U/L, ALP 74 U/L, Total Bilirubin 0.8 mg/dL. "
        "Metformin 500mg BID.\n\nA: Near target.\n\nP: Continue."
    )
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.return_value = _mock_response(full_note)
        result = optimize_note("Patient has full labs.")

    assert result["missing_fields"] == []


def test_optimize_note_on_api_failure_returns_original():
    with patch("extraction.optimize._client") as mock_client:
        mock_client.messages.create.side_effect = Exception("API error")
        result = optimize_note("Original note text.")

    assert result["optimized_note"] == "Original note text."
    assert result["missing_fields"] == []
