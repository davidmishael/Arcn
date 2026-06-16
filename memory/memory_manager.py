import db
from vector_store import VectorStore


# -------------------------
# Intents that signal a
# meaningful preference
# -------------------------
PREFERENCE_SIGNALS = {
    "get_weather": {
        "location": "default_city",
        "unit"    : "default_unit"
    }
}

# Minimum times an entity must appear
# before it's persisted as a preference
MIN_COUNT = 2


class MemoryManager:

    def __init__(self):

        # Create tables if they don't exist yet
        db.init_db()

        # Start a new session for this run
        self.session_id = db.start_session()

        # Boot the vector store — loads ChromaDB
        # and the sentence-transformers model
        self.vector_store = VectorStore()

        print(f"Memory: session {self.session_id} started")

    # -------------------------
    # Called AFTER routing —
    # saves the turn to history
    # and checks for preferences
    # -------------------------
    def save(self, packet: dict, response: str):

        # 1. Save the full turn to SQLite
        db.save_turn(self.session_id, packet, response)

        # 2. Get the row ID of the turn we just saved
        # so we can use it as the vector store ID
        # REPLACE WITH THIS
        turn_id  = db.save_turn(self.session_id, packet, response)
        raw_text = packet.get("entities", {}).get("raw_text", "")
        intent   = packet.get("intent", "")

        self.vector_store.add(
            turn_id  = turn_id,
            raw_text = raw_text,
            intent   = intent,
            response = response
        )

        # 4. Passively extract preferences from entities
        self._extract_preferences(packet)

    # -------------------------
    # Called BEFORE routing —
    # enriches the packet with
    # memory context
    # -------------------------
    def enrich(self, packet: dict) -> dict:

        entities = packet.get("entities", {})
        intent   = packet.get("intent", "")

        # Inject known preferences into entities
        # only if they aren't already present
        prefs = db.get_all_preferences()

        for pref_key, pref_value in prefs.items():

            # Map preference keys back to entity keys
            if pref_key == "default_city" and "location" not in entities:
                entities["location"] = pref_value

            elif pref_key == "default_unit" and "unit" not in entities:
                entities["unit"] = pref_value

        # Only fetch context for ask_question —
        # avoids unnecessary DB reads on every turn
        if intent == "ask_question":

            raw_text = entities.get("raw_text", "")

            # Recent turns from SQLite (last 6)
            entities["memory_context"] = db.get_recent_turns(n=6)

            # Semantically similar turns from ChromaDB
            # finds relevant past turns even from weeks ago
            if raw_text:
                entities["semantic_context"] = self.vector_store.query(
                    text = raw_text,
                    n    = 3
                )
            else:
                entities["semantic_context"] = []

        packet["entities"] = entities

        return packet

    # -------------------------
    # Passive preference
    # extraction from entities
    # -------------------------
    def _extract_preferences(self, packet: dict):

        intent   = packet.get("intent", "")
        entities = packet.get("entities", {})

        # Check if this intent carries preference signals
        signals = PREFERENCE_SIGNALS.get(intent, {})

        for entity_key, pref_key in signals.items():
            value = entities.get(entity_key)

            if value:
                # Write to DB — count tracked inside update_preference
                db.update_preference(pref_key, value)

    # -------------------------
    # Called when Arcn shuts
    # down — closes the session
    # -------------------------
    def close(self):

        db.end_session(self.session_id)
        print(f"Memory: session {self.session_id} closed")

    # -------------------------
    # Get recent turns for
    # external use (e.g. CC)
    # -------------------------
    def get_recent(self, n: int = 6) -> list:

        return db.get_recent_turns(n)