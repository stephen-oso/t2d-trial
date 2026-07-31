import json
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

_EMBED_FN = SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)


def embed_trials(
    trials_dir: str = "data/trials",
    db_path: str = "chroma_db",
) -> None:
    """Load all trial JSONs, embed eligibility text, store in ChromaDB."""
    client = chromadb.PersistentClient(path=db_path)
    collection = client.get_or_create_collection(
        name="trials",
        embedding_function=_EMBED_FN,
    )

    trial_files = list(Path(trials_dir).glob("*.json"))
    if not trial_files:
        raise FileNotFoundError(f"No trial JSON files found in {trials_dir}")

    documents, metadatas, ids = [], [], []

    for f in trial_files:
        trial = json.loads(f.read_text(encoding="utf-8"))
        # Embed the full eligibility text — this is what gets searched
        documents.append(trial["eligibility_text"])
        metadatas.append({
            "trial_id": trial["trial_id"],
            "title": trial["title"],
            "inclusion": json.dumps(trial["inclusion"]),
            "exclusion": json.dumps(trial["exclusion"]),
        })
        ids.append(trial["trial_id"])

    # upsert = add if new, update if exists
    collection.upsert(documents=documents, metadatas=metadatas, ids=ids)
    print(f"Embedded {len(documents)} trials into ChromaDB at {db_path}")


def get_chroma_collection(
    db_path: str = "chroma_db",
) -> chromadb.Collection:
    """Return the trials collection from ChromaDB."""
    client = chromadb.PersistentClient(path=db_path)
    return client.get_collection(
        name="trials",
        embedding_function=_EMBED_FN,
    )


if __name__ == "__main__":
    embed_trials()
