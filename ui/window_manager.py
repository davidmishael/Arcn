import os
import webview

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class Api:
    """Exposed to JS via window.pywebview.api"""
    def __init__(self):
        self._win = None  # set after window created

    def set_window(self, win):
        self._win = win

    def hide(self):
        if self._win:
            self._win.hide()

    # -------------------------
    # Notes CRUD — called directly
    # from JS via window.pywebview.api.*
    # Bypasses CommandCenter/router entirely —
    # a click isn't a voice command, no reason
    # to force it through NLP/intent classification.
    # -------------------------
    def get_all_notes(self):
        import sys, os
        sys.path.append(os.path.join(ROOT, "memory"))
        import db
        return db.get_recent_notes(50)

    def save_note_edit(self, note_id, content):
        import sys, os
        sys.path.append(os.path.join(ROOT, "memory"))
        import db
        success = db.update_note_content(int(note_id), content)
        return {"success": success}

    def delete_note_from_ui(self, note_id):
        import sys, os
        sys.path.append(os.path.join(ROOT, "memory"))
        import db
        success = db.delete_note(int(note_id))
        return {"success": success}
    
    def finish_voice_note(self, title, content):
        """
        Called when the user types + saves during a voice-triggered
        note creation, instead of letting the spoken content finish it.
        Creates the note directly and clears backend pending state so
        the voice flow doesn't also try to save separately.
        """
        import sys, os
        sys.path.append(os.path.join(ROOT, "memory"))
        sys.path.append(os.path.join(ROOT, "command_center"))
        import db
        from state import StateManager

        note_id = db.create_note(title, content)

        state = StateManager()
        state.clear_pending_note_stage()
        state.clear_pending_note_title()
        state.clear_pending_note_content()

        return {"success": True, "note_id": note_id}
    
    def clear_show_note_trigger(self):
        """
        Called when the notes grid is closed (either via the close
        button or after opening a note to edit). Without this,
        pending_show_note_id never gets cleared from SQLite and
        the grid auto-reopens on every future boot.
        """
        import sys, os
        sys.path.append(os.path.join(ROOT, "command_center"))
        from state import StateManager

        state = StateManager()
        state.clear_pending_show_note_id()

        return {"success": True}

def create_window(icon_path: str) -> tuple:
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "window.html")

    with open(html_path, "r") as f:
        html = f.read()

    api = Api()

    screens = webview.screens
    screen_width  = screens[0].width
    screen_height = screens[0].height

    win = webview.create_window(
        title            = "Arcn",
        html             = html,
        js_api           = api,
        width            = screen_width,
        height           = screen_height,
        x                = 0,
        y                = 0,
        frameless        = True,
        on_top           = True,
        background_color = "#0e0e0e",
        resizable        = False,
        hidden           = False,
    )

    api.set_window(win)
    return win, api