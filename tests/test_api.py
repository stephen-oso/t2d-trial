import pytest
from unittest.mock import patch
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


def test_optimize_endpoint_returns_optimized_note():
    with patch("api.main.optimize_note") as mock_opt:
        mock_opt.return_value = {
            "optimized_note": "S: Patient...\nO: HbA1c 7.6%...",
            "missing_fields": ["FPG", "OGTT"],
        }
        resp = client.post("/optimize", json={"note": "Patient has T2D. HbA1c 7.6%."})

    assert resp.status_code == 200
    data = resp.json()
    assert data["optimized_note"] == "S: Patient...\nO: HbA1c 7.6%..."
    assert data["missing_fields"] == ["FPG", "OGTT"]


def test_optimize_endpoint_rejects_short_note():
    resp = client.post("/optimize", json={"note": "hi"})
    assert resp.status_code == 422
