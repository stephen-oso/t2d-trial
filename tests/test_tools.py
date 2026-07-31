import json
from matching.tools import search_trials, check_eligibility, score_match


def test_search_trials_returns_json():
    result = search_trials.invoke("HbA1c blood sugar type 2 diabetes")
    data = json.loads(result)
    assert isinstance(data, list)
    assert len(data) >= 1
    assert "trial_id" in data[0]
    assert "inclusion" in data[0]


def test_check_eligibility_pass():
    patient = json.dumps({
        "age": 52, "hba1c": 8.2, "bmi": 29.4, "egfr": 85.0,
        "on_insulin": False, "current_medications": ["metformin"],
        "months_since_diagnosis": 18, "exclusion_flags": []
    })
    # Search for a trial first to get a real trial_id
    trials = json.loads(search_trials.invoke("type 2 diabetes HbA1c"))
    trial_id = trials[0]["trial_id"]

    result = check_eligibility.invoke(json.dumps({"patient_json": patient, "trial_id": trial_id}))
    data = json.loads(result)
    assert isinstance(data, list)
    assert all("criterion" in item and "status" in item for item in data)
    assert all(item["status"] in ("PASS", "FAIL", "UNKNOWN") for item in data)


def test_score_match_all_pass():
    verdicts = json.dumps([
        {"criterion": "HbA1c 7.5-10%", "status": "PASS", "patient_value": "8.2%"},
        {"criterion": "Age 30-70", "status": "PASS", "patient_value": "52"},
    ])
    result = score_match.invoke(verdicts)
    data = json.loads(result)
    assert data["score"] == 1.0
    assert data["missing"] == []


def test_score_match_with_unknown():
    verdicts = json.dumps([
        {"criterion": "HbA1c 7.5-10%", "status": "PASS", "patient_value": "8.2%"},
        {"criterion": "eGFR > 60", "status": "UNKNOWN", "patient_value": None},
    ])
    result = score_match.invoke(verdicts)
    data = json.loads(result)
    assert 0 < data["score"] < 1.0
    assert len(data["missing"]) == 1
