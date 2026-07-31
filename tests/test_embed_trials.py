import json
from pathlib import Path
from ingestion.embed_trials import embed_trials, get_chroma_collection


def test_embed_and_retrieve(tmp_path):
    # Write a fake trial JSON
    trial = {
        "trial_id": "NCT_TEST01",
        "title": "Test Diabetes Trial",
        "eligibility_text": "HbA1c must be between 7.5 and 10 percent.",
        "inclusion": ["HbA1c 7.5-10%", "Age 30-70"],
        "exclusion": ["On insulin therapy"],
    }
    (tmp_path / "NCT_TEST01.json").write_text(json.dumps(trial))

    # Embed into a temp ChromaDB
    db_path = str(tmp_path / "chroma")
    embed_trials(trials_dir=str(tmp_path), db_path=db_path)

    # Query it
    collection = get_chroma_collection(db_path=db_path)
    results = collection.query(
        query_texts=["blood sugar HbA1c eligibility"],
        n_results=1,
    )
    assert len(results["documents"][0]) == 1
    assert "NCT_TEST01" in results["metadatas"][0][0]["trial_id"]
