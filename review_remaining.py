import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

# Review the ones not yet assessed in detail
remaining = [
    "NCT06682481.json",
    "NCT06745544.json",
    "NCT06979440.json",
    "NCT07032844.json",
    "NCT07458516.json",
    "NCT05662462.json",
    "NCT05909046.json",
    "NCT07216508.json",
]

trials_dir = Path("data/trials")
for fname in remaining:
    f = trials_dir / fname
    if not f.exists():
        print(f"MISSING: {fname}")
        continue
    d = json.loads(f.read_text(encoding="utf-8"))
    text = d.get("eligibility_text", "")
    has_hba1c = "HbA1c" in text or "hemoglobin A1c" in text.lower() or "glycated" in text.lower() or "glycosylated" in text.lower()
    has_bmi = "BMI" in text or "body mass index" in text.lower()
    has_egfr = "eGFR" in text or "GFR" in text
    has_glucose = "glucose" in text.lower() or "blood sugar" in text.lower()
    print(f"=== {fname} ===")
    print(f"Title: {d['title']}")
    print(f"HbA1c={has_hba1c}, BMI={has_bmi}, eGFR={has_egfr}, glucose={has_glucose}")
    print(f"INCLUSION ({len(d['inclusion'])}):")
    for i, c in enumerate(d["inclusion"], 1):
        print(f"  {i}. {c[:130]}")
    print(f"EXCLUSION ({len(d['exclusion'])}):")
    for i, c in enumerate(d["exclusion"], 1):
        print(f"  {i}. {c[:130]}")
    print()
