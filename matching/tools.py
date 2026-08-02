import json
import os
import urllib.request
import urllib.parse
from dotenv import load_dotenv
from langchain_core.tools import tool
import anthropic

load_dotenv()

_CTGOV_BASE = "https://clinicaltrials.gov/api/v2"
_anthropic_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])


@tool
def search_trials(query: str) -> str:
    """Search ClinicalTrials.gov for recruiting T2D trials relevant to a patient.
    Returns a JSON list of trials with trial_id and title.
    Args:
        query: Short patient description used to find relevant trials.
    """
    params = urllib.parse.urlencode({
        "query.cond": "Type 2 Diabetes",
        "query.term": query,
        "filter.overallStatus": "RECRUITING",
        "pageSize": "10",
        "fields": "NCTId,BriefTitle",
    })
    url = f"{_CTGOV_BASE}/studies?{params}"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        data = json.loads(resp.read())

    trials = []
    for study in data.get("studies", []):
        proto = study.get("protocolSection", {})
        id_mod = proto.get("identificationModule", {})
        nct_id = id_mod.get("nctId", "")
        title = id_mod.get("briefTitle", "")
        if nct_id:
            trials.append({"trial_id": nct_id, "title": title})

    return json.dumps(trials)


@tool
def check_eligibility(input_json: str) -> str:
    """Check whether a patient meets eligibility criteria for one specific trial.
    Fetches live eligibility text from ClinicalTrials.gov, then evaluates with Claude.
    Input: JSON string with keys patient_json (str) and trial_id (str).
    Returns JSON list of {criterion, status, patient_value}.
    Status is PASS, FAIL, or UNKNOWN."""
    data = json.loads(input_json)
    trial_id = data["trial_id"]
    patient_raw = data.get("patient_json", "{}")
    patient = json.loads(patient_raw) if isinstance(patient_raw, str) else patient_raw

    # Fetch live trial eligibility text from ClinicalTrials.gov
    url = f"{_CTGOV_BASE}/studies/{trial_id}?fields=NCTId,BriefTitle,EligibilityModule"
    req = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as resp:
        study_data = json.loads(resp.read())

    proto = study_data.get("protocolSection", {})
    elig = proto.get("eligibilityModule", {})
    eligibility_text = elig.get("eligibilityCriteria", "")
    if not eligibility_text:
        return json.dumps([{
            "criterion": "eligibility criteria unavailable",
            "status": "UNKNOWN",
            "patient_value": None,
        }])

    prompt = f"""You are checking whether a patient meets clinical trial eligibility criteria.

Patient data:
{json.dumps(patient, indent=2)}

Trial eligibility criteria (from ClinicalTrials.gov):
{eligibility_text}

Return a JSON array where each item represents one criterion:
  {{"criterion": "<brief criterion text>", "status": "PASS"|"FAIL"|"UNKNOWN", "patient_value": "<relevant patient value as string, or null>"}}

Rules:
- Inclusion criteria: PASS if patient clearly meets it, FAIL if clearly not, UNKNOWN if data is missing.
- Exclusion criteria: PASS means patient does NOT have the exclusion (safe to include). FAIL means they DO (excluded).
- Numeric ranges: ">7.5%" means 7.5% is FAIL; "7.0-10.0%" means 7.5% is PASS. Be precise.
- Only mark FAIL when you are certain the patient does not qualify based on available data.
- Missing or null patient data for a criterion → UNKNOWN, never FAIL.

Return ONLY the JSON array, no explanation or other text."""

    response = _anthropic_client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],
    )

    text = response.content[0].text.strip()
    start = text.find("[")
    end = text.rfind("]") + 1
    if start >= 0 and end > start:
        verdicts = json.loads(text[start:end])
    else:
        verdicts = []

    verdicts = [v for v in verdicts if isinstance(v, dict) and "status" in v]
    return json.dumps(verdicts)


@tool
def score_match(verdicts_json: str) -> str:
    """Score a patient's overall match for a trial based on criterion verdicts.
    Input: JSON list of {criterion, status, patient_value} objects.
    Returns JSON: {score: float 0-1, missing: list[str]}.
    Score is 0.0 if any FAIL is present."""
    verdicts = json.loads(verdicts_json)
    if isinstance(verdicts, str):
        verdicts = json.loads(verdicts)

    normalized = []
    for v in verdicts:
        if isinstance(v, dict):
            normalized.append(v)
        elif isinstance(v, str) and v.strip():
            try:
                parsed = json.loads(v)
                if isinstance(parsed, dict):
                    normalized.append(parsed)
            except json.JSONDecodeError:
                pass
    verdicts = [v for v in normalized if "status" in v]

    passes = sum(1 for v in verdicts if v["status"] == "PASS")
    fails = sum(1 for v in verdicts if v["status"] == "FAIL")
    unknowns = sum(1 for v in verdicts if v["status"] == "UNKNOWN")
    missing = [v.get("criterion", "") for v in verdicts if v["status"] == "UNKNOWN"]

    if fails > 0:
        return json.dumps({"score": 0.0, "missing": missing})

    total = passes + fails
    if total == 0:
        score = 0.0
    else:
        base_score = passes / total
        unknown_penalty = min(unknowns * 0.05, 0.2)
        score = max(0.0, base_score - unknown_penalty)

    return json.dumps({"score": round(score, 3), "missing": missing})
