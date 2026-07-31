from pydantic import ValidationError
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
