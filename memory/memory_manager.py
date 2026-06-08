from html import entities
import db


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

        print(f"Memory: session {self.session_id} started")

    # -------------------------
    # Called AFTER routing —
    # saves the turn to history
    # and checks for preferences
    # -------------------------
    def save(self, packet: dict, response: str):

        # 1. Save the full turn to conversations
        db.save_turn(self.session_id, packet, response)

        # 2. Passively extract preferences from entities
        self._extract_preferences(packet)

    # -------------------------
    # Called BEFORE routing —
    # enriches the packet with
    # memory context
    # -------------------------
    def enrich(self, packet: dict) -> dict:

        entities = packet.get("entities", {})

        # Inject known preferences into entities
        # only if they aren't already present
        prefs = db.get_all_preferences()

        for pref_key, pref_value in prefs.items():

            # Map preference keys back to entity keys
            if pref_key == "default_city" and "location" not in entities:
                entities["location"] = pref_value

            elif pref_key == "default_unit" and "unit" not in entities:
                entities["unit"] = pref_value

        # Only fetch history for intents that need it
        # avoids unnecessary DB reads on every turn
        if packet.get("intent") == "ask_question":
            entities["memory_context"] = db.get_recent_turns(n=6)
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
                # Write to DB — count is tracked inside update_preference
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