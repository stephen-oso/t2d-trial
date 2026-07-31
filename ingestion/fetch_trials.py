import json
import os
import re
import requests
from pathlib import Path

CTGOV_API = "https://clinicaltrials.gov/api/v2/studies"


def _parse_criteria(text: str) -> tuple[list[str], list[str]]:
    """Split raw eligibility text into inclusion and exclusion lists."""
    inclusion, exclusion = [], []
    current = inclusion
    for line in text.splitlines():
        line = line.strip()
        if not line or line in ("Inclusion Criteria:", "Exclusion Criteria:"):
            if "Exclusion" in line:
                current = exclusion
            continue
        if line.startswith(("-", "*", "•")):
            line = line.lstrip("-*• ").strip()
        if line:
            current.append(line)
    return inclusion, exclusion


def fetch_and_save_trials(
    condition: str = "type 2 diabetes",
    max_results: int = 10,
    output_dir: str = "data/trials"
) -> list[str]:
    """Fetch trials from ClinicalTrials.gov and save as JSON files."""
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    params = {
        "query.cond": condition,
        "filter.overallStatus": "RECRUITING",
        "fields": "NCTId,BriefTitle,OverallStatus,EligibilityCriteria",
        "pageSize": max_results * 3,  # fetch more, filter down
    }

    response = requests.get(CTGOV_API, params=params, timeout=15)
    response.raise_for_status()
    studies = response.json().get("studies", [])

    saved = []
    for study in studies:
        if len(saved) >= max_results:
            break

        proto = study.get("protocolSection", {})
        nct_id = proto.get("identificationModule", {}).get("nctId", "")
        title = proto.get("identificationModule", {}).get("briefTitle", "")
        status = proto.get("statusModule", {}).get("overallStatus", "")
        elig_text = proto.get("eligibilityModule", {}).get("eligibilityCriteria", "")

        if not elig_text or not nct_id:
            continue

        inclusion, exclusion = _parse_criteria(elig_text)

        trial = {
            "trial_id": nct_id,
            "title": title,
            "status": status,
            "eligibility_text": elig_text,
            "inclusion": inclusion,
            "exclusion": exclusion,
        }

        path = Path(output_dir) / f"{nct_id}.json"
        path.write_text(json.dumps(trial, indent=2), encoding="utf-8")
        saved.append(str(path))

    return saved


if __name__ == "__main__":
    paths = fetch_and_save_trials()
    print(f"Saved {len(paths)} trials:")
    for p in paths:
        print(f"  {p}")
