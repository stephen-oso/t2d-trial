from pydantic import ValidationError

from extraction.extract import extract_patient_profile
from extraction.models import PatientProfile


def test_patient_profile_valid():
    p = PatientProfile(
        age=52,
        sex="female",
        hba1c=8.2,
        bmi=29.4,
        egfr=85.0,
        current_medications=["metformin 500mg"],
        on_insulin=False,
    )
    assert p.age == 52
    assert p.on_insulin is False
    assert p.months_since_diagnosis is None  # optional, not provided


def test_patient_profile_rejects_negative_age():
    try:
        PatientProfile(age=-5)
        assert False, "Should have raised"
    except ValidationError:
        pass


def test_patient_profile_defaults():
    p = PatientProfile()
    assert p.current_medications == []
    assert p.exclusion_flags == []
    assert p.on_insulin is False


def test_extract_basic_note():
    note = (
        "52-year-old female with Type 2 Diabetes diagnosed 18 months ago. "
        "HbA1c 8.2%, BMI 29.4, eGFR 85. On metformin 500mg twice daily. "
        "No insulin use."
    )
    profile = extract_patient_profile(note)
    assert profile.age == 52
    assert profile.hba1c == 8.2
    assert profile.on_insulin is False
    assert "metformin" in " ".join(profile.current_medications).lower()


def test_extract_insulin_flag():
    note = "65M, T2D for 10 years, HbA1c 9.1%, on insulin glargine 20 units nightly."
    profile = extract_patient_profile(note)
    assert profile.on_insulin is True


def test_extract_missing_fields_return_none():
    note = "Patient has Type 2 Diabetes. No other details provided."
    profile = extract_patient_profile(note)
    assert profile.hba1c is None
    assert profile.egfr is None
