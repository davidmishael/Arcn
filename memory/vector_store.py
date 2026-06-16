import chromadb
from chromadb.utils import embedding_functions
from pathlib import Path


# -------------------------
# Config
# -------------------------
DB_DIR          = Path(__file__).parent
CHROMA_PATH     = DB_DIR / "chroma_store"
COLLECTION_NAME = "arcn_conversations"
EMBED_MODEL     = "all-MiniLM-L6-v2"


# -------------------------
# Intents worth storing
# in the vector store —
# only conversational turns
# benefit from semantic search
# -------------------------
VECTOR_INTENTS = {
    "ask_question",
    "get_weather",
    "create_reminder",
    "take_note",
    "web_search"
}


class VectorStore:

    def __init__(self):

        # Persistent client — saves to disk in chroma_store/
        self.client = chromadb.PersistentClient(path=str(CHROMA_PATH))

        # Local sentence-transformers embedding model
        # runs fully offline — no API calls
        self.embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBED_MODEL
        )

        # Get or create the collection
        self.collection = self.client.get_or_create_collection(
            name      = COLLECTION_NAME,
            embedding_function = self.embed_fn,
            metadata  = {"hnsw:space": "cosine"}
        )

        print(f"Vector store ready — {self.collection.count()} turns indexed")

    # -------------------------
    # Add a turn to the store
    # Only stores intents that
    # benefit from semantic search
    # -------------------------
    def add(self, turn_id: int, raw_text: str, intent: str, response: str):

        if intent not in VECTOR_INTENTS:
            return

        if not raw_text or not raw_text.strip():
            return

        # Document is raw_text + response combined
        # gives richer semantic signal than text alone
        document = f"{raw_text} {response}".strip()

        # ChromaDB requires string IDs
        str_id = str(turn_id)

        # Check if this turn is already indexed
        # prevents duplicate entries on re-runs
        existing = self.collection.get(ids=[str_id])
        if existing["ids"]:
            return

        self.collection.add(
            ids        = [str_id],
            documents  = [document],
            metadatas  = [{
                "intent"  : intent,
                "raw_text": raw_text,
                "response": response
            }]
        )

    # -------------------------
    # Query for semantically
    # similar past turns
    # -------------------------
    def query(self, text: str, n: int = 3) -> list:

        if not text or not text.strip():
            return []

        # Need at least n documents to query
        if self.collection.count() < n:
            n = max(1, self.collection.count())

        if self.collection.count() == 0:
            return []

        results = self.collection.query(
            query_texts = [text],
            n_results   = n
        )

        # Unpack results into clean dicts
        turns = []

        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        for meta, distance in zip(metadatas, distances):

            # distance is cosine distance (0 = identical, 2 = opposite)
            # convert to similarity score (1 = identical, -1 = opposite)
            similarity = round(1 - distance, 3)
            # Only return turns with meaningful similarity
            if similarity < 0.2:
                continue

            turns.append({
                "raw_text"  : meta.get("raw_text", ""),
                "intent"    : meta.get("intent", ""),
                "response"  : meta.get("response", ""),
                "similarity": similarity
            })

        return turns

    # -------------------------
    # How many turns indexed
    # -------------------------
    def count(self) -> int:
        return self.collection.count()

    # -------------------------
    # Clear everything
    # -------------------------
    def reset(self):
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name               = COLLECTION_NAME,
            embedding_function = self.embed_fn,
            metadata           = {"hnsw:space": "cosine"}
        )
        print("Vector store cleared")