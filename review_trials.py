import json
from pathlib import Path

trials_dir = Path("data/trials")
files = sorted(trials_dir.glob("*.json"))
for f in files:
    d = json.loads(f.read_text(encoding="utf-8"))
    inc = d.get("inclusion", [])
    exc = d.get("exclusion", [])
    text = d.get("eligibility_text", "")
    has_hba1c = "HbA1c" in text or "hemoglobin A1c" in text.lower() or "glycated" in text.lower()
    has_bmi = "BMI" in text or "body mass index" in text.lower()
    has_egfr = "eGFR" in text or "GFR" in text
    print(f"{f.name}: inc={len(inc)}, exc={len(exc)}, HbA1c={has_hba1c}, BMI={has_bmi}, eGFR={has_egfr}")
    title = d["title"][:80]
    print(f"  Title: {title}")
    print()
