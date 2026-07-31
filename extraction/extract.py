import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from extraction.models import PatientProfile

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), "..", ".env"))  # project-level .env only

# Groq is OpenAI-compatible — same SDK, different base URL
_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
    max_retries=6,  # retry on 429 rate-limit errors with exponential backoff
)

_SYSTEM_PROMPT = """You extract structured patient data from clinical notes.
Return ONLY valid JSON matching this exact schema — no explanation, no markdown:
{
  "age": integer or null,
  "sex": "male" or "female" or null,
  "months_since_diagnosis": integer or null,
  "hba1c": float or null,
  "bmi": float or null,
  "egfr": float or null,
  "current_medications": [list of strings],
  "on_insulin": true or false,
  "exclusion_flags": [list of strings describing disqualifying conditions]
}
If a field is not mentioned, return null for scalars and [] for lists.
on_insulin is true only if the patient currently uses any insulin product."""


def extract_patient_profile(note: str) -> PatientProfile:
    """Extract a structured PatientProfile from an unstructured clinical note."""
    response = _client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": f"Extract from this note:\n\n{note}"},
        ],
        response_format={"type": "json_object"},
        temperature=0,  # deterministic — we want consistent extraction
    )

    raw = json.loads(response.choices[0].message.content)
    return PatientProfile(**raw)
