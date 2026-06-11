

# -------------------------
# Intent + entity → tool key
# -------------------------
INTENT_MAP = {

    # open_app → which app
    ("open_app", "youtube")  : "open_youtube",
    ("open_app", "google")   : "open_google",
    ("open_app", "chatgpt")  : "open_chatgpt",
    ("open_app", "terminal") : "open_terminal",
    ("open_app", "notes")    : "open_notes",
    ("open_app", "finder")   : "open_finder",
    ("open_app", "settings") : "open_settings",
    ("open_app", "vs code")  : "open_vscode",
    ("open_app", "vscode")   : "open_vscode",
    ("open_app", "chat gpt") : "open_chatgpt",

    # close
    ("close_app", None)          : "close_app",

    # volume
    ("system_volume", "up")      : "system_volume_up",
    ("system_volume", "down")    : "system_volume_down",
    ("system_volume", "mute")    : "mute_volume",

    # brightness
    ("system_brightness", "up")  : "system_brightness_up",
    ("system_brightness", "down"): "system_brightness_down",

    # searches
    ("web_search", "youtube")    : "search_youtube",
    ("web_search", "google")     : "search_google",
    ("web_search", None)         : "search_google",

    # timer
    ("set_timer", None)          : "set_timer",
    ("cancel_timer", None)       : "cancel_timer",

    # time + date
    ("tell_time", None)          : "tell_time",
    ("tell_date", None)          : "tell_date",

    # notes
    ("take_note", None)          : "take_note",

    # personality
    ("greet", None)              : "greet",
    ("how_are_you", None)        : "how_are_you",
    ("stop_cancel", None)        : "stop_cancel",

    # modes
    ("open_app", "developer")    : "developer_mode",
    ("open_app", "study")        : "study_mode",

    # coming soon
    ("play_music", None)         : "play_music",
    ("pause_music", None)        : "pause_music",
    ("skip_song", None)          : "skip_song",
    ("get_weather", None)        : "get_weather",
    ("send_message", None)       : "send_message",
    ("ask_question", None)       : "ask_question",
    ("create_reminder", None)    : "create_reminder",
    ("lock_mac", None) : "lock_mac",
}


class Router:

    def __init__(self, tools: dict):

        # Action registry injected from tools module
        self.tools = tools

        # Memory not connected yet
        # self.memory = load_memory()

    # -------------------------
    # Route intent → tool key
    # -------------------------
    def _resolve_tool_key(self, intent: str, entities: dict) -> str:

        app       = entities.get("app")
        direction = entities.get("direction")

        # Try with app entity first
        if app:
            key = INTENT_MAP.get((intent, app))
            if key:
                return key

        # Try with direction entity
        if direction:
            key = INTENT_MAP.get((intent, direction))
            if key:
                return key

        # Try intent with no entity (fallback)
        key = INTENT_MAP.get((intent, None))
        if key:
            return key

        # Last resort — direct match in tools registry
        return intent

    # -------------------------
    # Route intent → action
    # -------------------------
    def route(self, intent: str, entities: dict, source: str) -> dict:

        tool_key = self._resolve_tool_key(intent, entities)
        tool     = self.tools.get(tool_key)

        if not tool:
            return self._no_tool(intent)

        try:
            result = tool["function"](entities)

            # Use returned value as response if available
            # otherwise fall back to confirmation string
            response = result if isinstance(result, str) and result else tool.get("confirmation", "Done.")

            return self._response(
                status       = "executed",
                intent       = intent,
                response     = response,
                action_taken = True
            )

        except Exception as e:
            return self._response(
                status       = "failed",
                intent       = intent,
                response     = f"Something went wrong: {e}",
                action_taken = False
            )

    # -------------------------
    # No matching tool found
    # -------------------------
    def _no_tool(self, intent: str) -> dict:

        return self._response(
            status       = "unknown",
            intent       = intent,
            response     = "I understood you but I don't know how to do that yet.",
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