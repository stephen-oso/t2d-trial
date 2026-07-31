import json
import threading
from pathlib import Path
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction

# ── Module-level singletons created in the main thread ───────────────────────
# ChromaDB's Rust backend (RustBindingsAPI) must be initialised in the same
# thread that will use it.  Creating new PersistentClient objects inside worker
# threads (as LangGraph does) triggers an AttributeError.  The fix is to
# initialise once at import time (main thread) and share the collection object.
_EMBED_FN = SentenceTransformerEmbeddingFunction(model_name="all-MiniLM-L6-v2")

_DEFAULT_DB_PATH = "chroma_db"
_collection_cache: dict[str, chromadb.Collection] = {}
_cache_lock = threading.Lock()


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
    # Invalidate cache so get_chroma_collection returns fresh data
    with _cache_lock:
        _collection_cache.pop(db_path, None)
    print(f"Embedded {len(documents)} trials into ChromaDB at {db_path}")


def get_chroma_collection(
    db_path: str = "chroma_db",
) -> chromadb.Collection:
    """Return the trials collection from ChromaDB.

    The collection object is cached the first time it is requested (from the
    main thread or the first worker thread that calls it).  Subsequent calls
    from any thread reuse the cached object, which avoids reinitialising the
    ChromaDB Rust backend inside worker threads.
    """
    with _cache_lock:
        if db_path not in _collection_cache:
            client = chromadb.PersistentClient(path=db_path)
            _collection_cache[db_path] = client.get_collection(
                name="trials",
                embedding_function=_EMBED_FN,
            )
        return _collection_cache[db_path]


if __name__ == "__main__":
    embed_trials()
