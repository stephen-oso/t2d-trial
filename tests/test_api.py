import pytest
from fastapi.testclient import TestClient
from api.main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["model"] == "gemma2-9b-it"


def test_trials_list():
    response = client.get("/trials")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 10
    assert "trial_id" in data[0]


def test_match_empty_note_returns_422():
    response = client.post("/match", json={"note": ""})
    assert response.status_code == 422


def test_metrics_endpoint():
    response = client.get("/metrics")
    assert response.status_code == 200
    data = response.json()
    assert "total_requests" in data
    assert "avg_latency_ms" in data


@pytest.mark.slow
def test_match_endpoint():
    payload = {
        "note": "52F, T2D 18 months, HbA1c 8.2%, BMI 29.4, eGFR 85, metformin, no insulin."
    }
    response = client.post("/match", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "patient" in data
    assert "matches" in data
