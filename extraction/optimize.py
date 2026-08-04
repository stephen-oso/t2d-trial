import os
import re
import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

_PLACEHOLDER = "[not found — add if available]"

# (keyword in original note, short display name for missing_fields list)
_FIELDS = [
    ("hba1c",           "HbA1c"),
    ("fasting",         "FPG"),
    ("ogtt",            "OGTT"),
    ("bmi",             "BMI"),
    ("egfr",            "eGFR"),
    ("ast",             "AST"),
    ("alt",             "ALT"),
    ("alp",             "ALP"),
    ("bilirubin",       "Bilirubin"),
    ("age",             "Age"),
    ("sex",             "Sex"),
    ("diagnosis",       "Diagnosis Duration"),
    ("medication",      "Medications"),
    ("insulin",         "Insulin Use"),
]

_SYSTEM = f"""You are a clinical documentation assistant for a T2D clinical trial pre-screener.

Rewrite the provided clinical note as a clean, well-structured SOAP note (S, O, A, P sections).

Rules:
1. Preserve ALL existing clinical values exactly — never change numbers or facts.
2. In the O (Objective) section, add the placeholder "{_PLACEHOLDER}" for each of these fields if they are NOT mentioned anywhere in the original note:
   - HbA1c (%)
   - Fasting Plasma Glucose / FPG (mg/dL)
   - OGTT 2-hour glucose (mg/dL)
   - BMI (kg/m²)
   - eGFR (mL/min/1.73m²)
   - AST (U/L)
   - ALT (U/L)
   - ALP (U/L)
   - Total Bilirubin (mg/dL)
   - Patient age
   - Patient sex
   - Duration since T2D diagnosis
   - Current medications (full list)
   - Insulin use (yes/no)
3. Do NOT invent or estimate any clinical values.
4. Return ONLY the rewritten SOAP note — no explanation, no preamble."""


def optimize_note(note: str) -> dict:
    try:
        response = _client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1024,
            system=_SYSTEM,
            messages=[{"role": "user", "content": f"Rewrite this note:\n\n{note}"}],
        )
        optimized = response.content[0].text.strip()
        note_lower = note.lower()
        missing = [
            display
            for keyword, display in _FIELDS
            if keyword not in note_lower
            and bool(re.search(
                re.escape(display) + r"[^.\n]*" + re.escape(_PLACEHOLDER),
                optimized,
                re.IGNORECASE,
            ))
        ]
        return {"optimized_note": optimized, "missing_fields": missing}
    except Exception:
        return {"optimized_note": note, "missing_fields": []}
