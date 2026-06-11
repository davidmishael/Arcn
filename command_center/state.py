import sys
import os

# -------------------------
# Point to memory module so
# we can import db directly
# -------------------------
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../memory")))

import db


class StateManager:

    def __init__(self):
        # Ensure the state table exists
        # init_db is safe to call multiple times — uses CREATE IF NOT EXISTS
        db.init_db()

        # Boot default state if keys don't exist yet
        if db.get_state_value("listening") is None:
            db.set_state_value("listening", "true")

    # -------------------------
    # Check if listening
    # -------------------------
    def is_listening(self) -> bool:
        return db.get_state_value("listening", "true") == "true"

    # -------------------------
    # Set listening on/off
    # -------------------------
    def set_listening(self, value: bool):
        db.set_state_value("listening", "true" if value else "false")

    # -------------------------
    # Toggle listening
    # -------------------------
    def toggle_listening(self) -> bool:
        current = self.is_listening()
        new = not current
        self.set_listening(new)
        return new

    # -------------------------
    # Track last intent
    # -------------------------
    def set_last_intent(self, intent: str):
        db.set_state_value("last_intent", intent)

    def get_last_intent(self) -> str:
        return db.get_state_value("last_intent", "")

    # -------------------------
    # Pending reminder topic
    # -------------------------
    def set_pending_reminder(self, topic: str):
        db.set_state_value("pending_reminder_topic", topic)

    def get_pending_reminder(self) -> str:
        return db.get_state_value("pending_reminder_topic", "")

    def clear_pending_reminder(self):
        db.delete_state_value("pending_reminder_topic")

    # -------------------------
    # Pending reminder date
    # -------------------------
    def set_pending_date(self, relative_time: str):
        db.set_state_value("pending_reminder_date", relative_time)

    def get_pending_date(self) -> str:
        return db.get_state_value("pending_reminder_date", "")

    def clear_pending_date(self):
        db.delete_state_value("pending_reminder_date")