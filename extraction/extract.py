import json
import os

import anthropic
from dotenv import load_dotenv

from extraction.models import PatientProfile

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))  # project-level .env only

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_SYSTEM_PROMPT = """You extract structured patient data from clinical notes.
Return ONLY valid JSON matching this exact schema — no explanation, no markdown:
{
  "age": integer or null,
  "sex": "male" or "female" or null,
  "months_since_diagnosis": integer or null,
  "hba1c": float or null,
  "fasting_glucose": float or null,
  "ogtt_2hr": float or null,
  "bmi": float or null,
  "egfr": float or null,
  "ast": float or null,
  "alt": float or null,
  "alp": float or null,
  "bilirubin": float or null,
  "current_medications": [list of strings],
  "on_insulin": true or false,
  "exclusion_flags": [list of strings describing disqualifying conditions]
}
If a field is not mentioned, return null for scalars and [] for lists.
on_insulin is true only if the patient currently uses any insulin product.
fasting_glucose is Fasting Plasma Glucose in mg/dL. ogtt_2hr is the 2-hour OGTT glucose in mg/dL.
ast, alt, alp are liver enzymes in U/L. bilirubin is total bilirubin in mg/dL."""


def extract_patient_profile(note: str) -> PatientProfile:
    """Extract a structured PatientProfile from an unstructured clinical note."""
    response = _client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=512,
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Extract from this note:\n\n{note}"}],
    )

    text = response.content[0].text.strip()
    start = text.find("{")
    end = text.rfind("}") + 1
    if start < 0 or end <= start:
        raise ValueError(f"No JSON object found in extraction response: {text[:200]}")
    raw = json.loads(text[start:end])
    return PatientProfile(**raw)
