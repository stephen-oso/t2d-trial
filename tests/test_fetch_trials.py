import json
import os
from pathlib import Path
from ingestion.fetch_trials import fetch_and_save_trials


def test_fetch_saves_json_files(tmp_path):
    paths = fetch_and_save_trials(
        condition="type 2 diabetes",
        max_results=3,
        output_dir=str(tmp_path)
    )
    assert len(paths) == 3
    for p in paths:
        assert Path(p).exists()
        data = json.loads(Path(p).read_text())
        assert "trial_id" in data
        assert "eligibility_text" in data
        assert isinstance(data["inclusion"], list)
        assert isinstance(data["exclusion"], list)
