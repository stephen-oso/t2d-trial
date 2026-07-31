import json
import os
import time
from openai import OpenAI, RateLimitError
from dotenv import load_dotenv
from langchain_core.tools import tool

load_dotenv()


def _get_collection():
    """Return a collection object for whichever vector store backend is active.

    If QDRANT_URL is set in the environment and the Qdrant cluster is reachable,
    returns a QdrantCollection wrapper that speaks the same query/get interface
    as a ChromaDB collection.  Otherwise falls back to ChromaDB (local dev / test).
    """
    if os.environ.get("QDRANT_URL"):
        # Production: use Qdrant Cloud
        try:
            from ingestion.embed_trials_qdrant import get_qdrant_client, _EMBED_MODEL, COLLECTION_NAME
            from qdrant_client.models import Filter, FieldCondition, MatchAny

            client = get_qdrant_client()
            # Verify connectivity — raises if the cluster is unreachable
            client.get_collections()

            class QdrantCollection:
                def query(self, query_texts, n_results=5):
                    vec = _EMBED_MODEL.encode(query_texts[0]).tolist()
                    response = client.query_points(
                        collection_name=COLLECTION_NAME,
                        query=vec,
                        limit=n_results,
                    )
                    metadatas = [[pt.payload for pt in response.points]]
                    return {"metadatas": metadatas}

                def get(self, ids, include=None):
                    results = client.scroll(
                        collection_name=COLLECTION_NAME,
                        scroll_filter=Filter(
                            must=[FieldCondition(key="trial_id", match=MatchAny(any=ids))]
                        ),
                    )[0]
                    return {"metadatas": [r.payload for r in results]}

            return QdrantCollection()
        except Exception as exc:
            # Qdrant URL is set but cluster is unreachable (e.g. placeholder creds,
            # no network in CI).  Fall back to ChromaDB so local tests still pass.
            import logging
            logging.getLogger(__name__).warning(
                "Qdrant unreachable (%s: %s) — falling back to ChromaDB",
                type(exc).__name__, exc,
            )

    # Local dev / test / Qdrant unreachable: use ChromaDB
    from ingestion.embed_trials import get_chroma_collection
    return get_chroma_collection()


_client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=os.environ["GROQ_API_KEY"],
    max_retries=6,  # retry on 429 with exponential backoff
)


@tool
def search_trials(query: str) -> str:
    """Search the clinical trial database for trials relevant to a patient query.
    Returns a JSON list of trials with their eligibility criteria."""
    collection = _get_collection()
    results = collection.query(query_texts=[query], n_results=10)

    trials = []
    for i, meta in enumerate(results["metadatas"][0]):
        trials.append({
            "trial_id": meta["trial_id"],
            "title": meta["title"],
            "inclusion": json.loads(meta["inclusion"]),
            "exclusion": json.loads(meta["exclusion"]),
        })

    return json.dumps(trials)


@tool
def check_eligibility(input_json: str) -> str:
    """Check a patient's eligibility against a specific trial's criteria.
    Input must be a JSON string with keys: patient_json (str) and trial_id (str).
    Example input: '{"patient_json": "{...}", "trial_id": "NCT00000001"}'
    Returns a JSON list of { criterion, status, patient_value } objects.
    Status is PASS, FAIL, or UNKNOWN."""
    data = json.loads(input_json)
    trial_id = data["trial_id"]

    # Handle both {"patient_json": "<JSON string>", ...} and {"patient": {...}, ...}
    if "patient_json" in data:
        patient_raw = data["patient_json"]
        patient = json.loads(patient_raw) if isinstance(patient_raw, str) else patient_raw
    elif "patient" in data:
        patient = data["patient"]
    else:
        # Maybe the patient fields are directly in the data dict minus trial_id
        patient = {k: v for k, v in data.items() if k != "trial_id"}


    # Get the trial criteria from the active vector store backend
    collection = _get_collection()
    result = collection.get(ids=[trial_id], include=["metadatas"])
    if not result["metadatas"]:
        return json.dumps([{"criterion": "trial not found", "status": "UNKNOWN", "patient_value": None}])

    meta = result["metadatas"][0]
    inclusion = json.loads(meta["inclusion"])
    exclusion = json.loads(meta["exclusion"])

    all_criteria = (
        [f"INCLUDE: {c}" for c in inclusion] +
        [f"EXCLUDE: {c}" for c in exclusion]
    )

    prompt = f"""You are checking if a patient meets clinical trial eligibility criteria. Be strict and precise.

Patient data:
{json.dumps(patient, indent=2)}

Criteria to check (each starts with INCLUDE or EXCLUDE):
{chr(10).join(f"- {c}" for c in all_criteria)}

For each criterion, return a JSON array. Each item must have:
- "criterion": the criterion text (without INCLUDE/EXCLUDE prefix)
- "status": "PASS", "FAIL", or "UNKNOWN" (UNKNOWN only if the patient data truly lacks the required info)
- "patient_value": the relevant patient value as a string, or null if unknown

Rules:
- For INCLUDE criteria: PASS if the patient clearly meets it, FAIL if they clearly do not, UNKNOWN if data is missing.
- For EXCLUDE criteria: PASS means the patient does NOT have the exclusion (safe to include). FAIL means they DO have it (excluded).
- Apply numeric comparisons strictly: if a criterion says ">7.5%" and the patient has exactly 7.5%, that is FAIL (not PASS).
- If a criterion says ">=45" and the patient has exactly 45, that is PASS.
- If the patient data has null or missing for a required field, mark UNKNOWN — do not assume.
- If the patient has a disqualifying condition that is explicitly listed as an exclusion, mark FAIL.
Return ONLY the JSON array, no explanation."""

    response = _client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"},
        temperature=0,
    )

    # The model may return {"verdicts": [...]} or similar — extract the list
    raw = json.loads(response.choices[0].message.content)

    # Normalize to a flat list of verdict dicts
    if isinstance(raw, list):
        # Sometimes model returns [{}, [...actual data...]] — flatten and filter
        verdicts = []
        for item in raw:
            if isinstance(item, list):
                verdicts.extend(item)
            elif isinstance(item, dict) and item:  # skip empty dicts
                verdicts.append(item)
    elif isinstance(raw, dict):
        # e.g. {"verdicts": [...]} — get the first list value
        for val in raw.values():
            if isinstance(val, list):
                verdicts = val
                break
        else:
            verdicts = []
    else:
        verdicts = []

    # Filter out items that don't have the expected "status" key
    verdicts = [v for v in verdicts if isinstance(v, dict) and "status" in v]
    return json.dumps(verdicts)


@tool
def score_match(verdicts_json: str) -> str:
    """Score a patient's overall match for a trial based on criterion verdicts.
    Input: JSON list of { criterion, status, patient_value } objects.
    Returns JSON: { score: float 0-1, missing: list[str] }
    Score = (PASS count) / (PASS + FAIL count). UNKNOWN criteria lower the score slightly.
    Score is 0.0 if any FAIL is present."""
    verdicts = json.loads(verdicts_json)

    passes = sum(1 for v in verdicts if v["status"] == "PASS")
    fails = sum(1 for v in verdicts if v["status"] == "FAIL")
    unknowns = sum(1 for v in verdicts if v["status"] == "UNKNOWN")
    missing = [v["criterion"] for v in verdicts if v["status"] == "UNKNOWN"]

    # Any FAIL means this trial is not a match
    if fails > 0:
        return json.dumps({"score": 0.0, "missing": missing})

    total = passes + fails
    if total == 0:
        score = 0.0
    else:
        base_score = passes / total
        # Each unknown criterion docks 0.05 (max 0.2 dock)
        unknown_penalty = min(unknowns * 0.05, 0.2)
        score = max(0.0, base_score - unknown_penalty)

    return json.dumps({"score": round(score, 3), "missing": missing})
