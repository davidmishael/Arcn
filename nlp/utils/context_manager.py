from collections import deque
from html import entities


# -------------------------
# Config
# -------------------------
MAX_HISTORY = 10  # how many turns to remember


class ContextManager:

    def __init__(self):

        # Sliding window of past turns
        self.history = deque(maxlen=MAX_HISTORY)

        # Accumulated slots across conversation
        self.slots = {} # now nested: {intent: {entity_key: value}}

        # Most recent intent + entities
        self.last_intent   = None
        self.last_entities = {}
        self.last_message  = None

    # -------------------------
    # Save latest interaction
    # -------------------------
    def update_context(self, intent: str, entities: dict, message: str):

        # Build turn object
        turn = {
            "message" : message,
            "intent"  : intent,
            "entities": entities
        }

        # Add to history window
        self.history.append(turn)

        # Update last turn
        self.last_intent   = intent
        self.last_entities = entities
        self.last_message  = message

        # Merge new entities into running slots
        # New values overwrite old ones for the same key
        if intent not in self.slots:
            self.slots[intent] = {}
        self.slots[intent].update(entities)

    # -------------------------
    # Return current context
    # -------------------------
    def get_context(self):

        return {
            "last_intent"   : self.last_intent,
            "last_entities" : self.last_entities,
            "last_message"  : self.last_message,
            "slots": dict(self.slots.get(self.last_intent, {})),
            "history"       : list(self.history)
        }

    # -------------------------
    # Get last N turns
    # -------------------------
    def get_recent_history(self, n: int = 3):

        turns = list(self.history)
        return turns[-n:] if len(turns) >= n else turns

    # -------------------------
    # Check if slot exists
    # -------------------------
    def get_slot(self, key: str):

        return self.slots.get(key, None)

    # -------------------------
    # Resolve pronouns / references
    # -------------------------
    def resolve_reference(self, text: str) -> dict:

        text_lower = text.lower()
        resolved   = {}

        vague_refs = ["it", "that", "this", "the same"]
        words = text_lower.split()

        # Only treat as a reference if the message is short — genuine
        # pointer-word follow-ups are brief ("do that again", "make it 10pm"),
        # not full sentences that happen to contain a common word like "this".
        if len(words) <= 5 and any(ref in words for ref in vague_refs):
            if self.last_intent:
                resolved["intent"]   = self.last_intent
                resolved["entities"] = self.last_entities.copy()

        return resolved
    # -------------------------
    # Detect follow-up
    # -------------------------
    def is_follow_up(self, text: str) -> bool:

        follow_up_phrases = [
            "make it",
            "change it",
            "instead",
            "do that",
            "update it",
            "again",
            "same thing",
            "like before",
            "but make",
            "actually",
            "wait no",
            "no make it",
            "switch it to",
            "at ",
            "by ",
            "pm",
            "am",
            "o'clock",
            "in the morning",
            "in the evening",
            "tonight",
            "tomorrow at"
        ]

        text_lower = text.lower()

        return any(phrase in text_lower for phrase in follow_up_phrases)

    # -------------------------
    # Clear everything
    # -------------------------
    def clear_context(self):

        self.history.clear()
        self.slots         = {}
        self.last_intent   = None
        self.last_entities = {}
        self.last_message  = None

    # -------------------------
    # Clear just one intent's
    # slot whiteboard
    # -------------------------
    def clear_slots_for_intent(self, intent: str):

        if intent in self.slots:
            self.slots[intent] = {}

    # -------------------------
    # Debug view
    # -------------------------
    def summary(self) -> str:

        lines = [
            f"History  : {len(self.history)} turns",
            f"Slots    : {self.slots}",
            f"Last     : {self.last_intent} — {self.last_message}"
        ]

        return "\n".join(lines)