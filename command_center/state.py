import json
import os


STATE_FILE = "assistant_state.json"


class StateManager:

    def __init__(self):

        # Boot with default state if file doesn't exist
        if not os.path.exists(STATE_FILE):
            self._write({"listening": True})

    # -------------------------
    # Get full state
    # -------------------------
    def get_state(self) -> dict:

        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)

        except Exception:
            return {"listening": True}

    # -------------------------
    # Check if listening
    # -------------------------
    def is_listening(self) -> bool:

        return self.get_state().get("listening", True)

    # -------------------------
    # Set listening on/off
    # -------------------------
    def set_listening(self, value: bool):

        state = self.get_state()
        state["listening"] = value
        self._write(state)

    # -------------------------
    # Toggle listening
    # -------------------------
    def toggle_listening(self) -> bool:

        current = self.is_listening()
        new     = not current
        self.set_listening(new)
        return new

    # -------------------------
    # Write state to disk
    # -------------------------
    def _write(self, state: dict):

        with open(STATE_FILE, "w") as f:
            json.dump(state, f, indent=4)

    # -------------------------
    # Track last intent
    # -------------------------
    def set_last_intent(self, intent: str):
        state = self.get_state()
        state["last_intent"] = intent
        self._write(state)

    def get_last_intent(self) -> str:
        return self.get_state().get("last_intent", "")

    # -------------------------
    # Pending reminder topic
    # -------------------------
    def set_pending_reminder(self, topic: str):
        state = self.get_state()
        state["pending_reminder_topic"] = topic
        self._write(state)

    def get_pending_reminder(self) -> str:
        return self.get_state().get("pending_reminder_topic", "")

    def clear_pending_reminder(self):
        state = self.get_state()
        state.pop("pending_reminder_topic", None)
        self._write(state)

    # -------------------------
    # Pending reminder date
    # -------------------------
    def set_pending_date(self, relative_time: str):
        state = self.get_state()
        state["pending_reminder_date"] = relative_time
        self._write(state)

    def get_pending_date(self) -> str:
        return self.get_state().get("pending_reminder_date", "")

    def clear_pending_date(self):
        state = self.get_state()
        state.pop("pending_reminder_date", None)
        self._write(state)