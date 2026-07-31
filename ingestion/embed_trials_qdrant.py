import json
import os
from pathlib import Path
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct
from sentence_transformers import SentenceTransformer

load_dotenv()

_EMBED_MODEL = SentenceTransformer("all-MiniLM-L6-v2")
COLLECTION_NAME = "trials"
VECTOR_SIZE = 384  # all-MiniLM-L6-v2 output dimension


def get_qdrant_client() -> QdrantClient:
    return QdrantClient(
        url=os.environ["QDRANT_URL"],
        api_key=os.environ["QDRANT_API_KEY"],
    )


def embed_trials_qdrant(trials_dir: str = "data/trials") -> None:
    """Embed all trials and upload to Qdrant Cloud."""
    client = get_qdrant_client()

    # Create collection if it doesn't exist
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE),
        )

    trial_files = list(Path(trials_dir).glob("*.json"))
    points = []

    for i, f in enumerate(trial_files):
        trial = json.loads(f.read_text())
        vector = _EMBED_MODEL.encode(trial["eligibility_text"]).tolist()
        points.append(PointStruct(
            id=i,
            vector=vector,
            payload={
                "trial_id": trial["trial_id"],
                "title": trial["title"],
                "inclusion": json.dumps(trial["inclusion"]),
                "exclusion": json.dumps(trial["exclusion"]),
            },
        ))

    client.upsert(collection_name=COLLECTION_NAME, points=points)
    print(f"Uploaded {len(points)} trials to Qdrant Cloud")


if __name__ == "__main__":
    embed_trials_qdrant()
