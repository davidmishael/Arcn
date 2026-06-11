import sys
import os

sys.path.append(os.path.abspath("../memory"))

from router import Router
from state import StateManager
from memory_manager import MemoryManager


# Intents that should ALWAYS take priority
# These skip memory entirely — no DB read needed
PRIORITY_INTENTS = {
    "stop_cancel", "greet", "how_are_you",
    "tell_time", "tell_date", "cancel_timer"
}


class CommandCenter:

    def __init__(self, tools: dict):

        # Router handles intent → action mapping
        self.router = Router(tools)

        # State manages system-level state
        self.state = StateManager()

        # Memory — persistent context across sessions
        self.memory = MemoryManager()

    # -------------------------
    # Main entry point
    # -------------------------
    def handle(self, packet: dict) -> dict:

        source     = packet.get("source", "nlp")
        intent     = packet.get("intent")
        entities   = packet.get("entities", {})
        requires_clarification = packet.get("requires_clarification", False)

        # -------------------------
        # Priority intents skip
        # memory entirely — fast path
        # -------------------------
        if intent in PRIORITY_INTENTS:
            # If a reminder is pending, a time response takes priority
            # over tell_time — user is answering our clarification question
            if intent == "tell_time" and self.state.get_pending_reminder():
                intent = "create_reminder"
            else:
                self.state.set_last_intent(intent)
                return self.router.route(intent, entities, source)

        # -------------------------
        # Unknown / clarification
        # handling — same as before
        # -------------------------
        if intent == "unknown_intent" or requires_clarification:
            last = self.state.get_last_intent()

            if last == "ask_question":
                intent = "ask_question"
                requires_clarification = False

            elif last == "create_reminder":
                intent = "create_reminder"
                requires_clarification = False

            elif intent == "unknown_intent":
                return self._unknown()

            else:
                return self._clarify(intent, entities)

        # -------------------------
        # Memory injection point —
        # enrich packet BEFORE routing
        # -------------------------
        packet = self.memory.enrich(packet)

        # -------------------------
        # Route to tool
        # -------------------------
        self.state.set_last_intent(intent)
        result = self.router.route(intent, packet["entities"], source)

        # -------------------------
        # Save turn to memory
        # AFTER routing completes
        # -------------------------
        self.memory.save(packet, result.get("response", ""))

        return result

    # -------------------------
    # Shutdown — close memory
    # session cleanly
    # -------------------------
    def shutdown(self):
        self.memory.close()

    # -------------------------
    # Clarification response
    # -------------------------
    def _clarify(self, intent: str, entities: dict) -> dict:

        return self._response(
            status       = "clarifying",
            intent       = intent,
            response     = "I'm not quite sure what you mean — could you say that again?",
            action_taken = False
        )

    # -------------------------
    # Unknown intent response
    # -------------------------
    def _unknown(self) -> dict:

        return self._response(
            status       = "unknown",
            intent       = "unknown_intent",
            response     = "I didn't catch that — could you repeat it?",
            action_taken = False
        )

    # -------------------------
    # Standard response packet
    # -------------------------
    def _response(
        self,
        status      : str,
        intent      : str,
        response    : str,
        action_taken: bool
    ) -> dict:

        return {
            "status"      : status,
            "intent"      : intent,
            "response"    : response,
            "action_taken": action_taken
        }