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

def create_window(icon_path: str) -> tuple:
    """
    Returns (window, api).
    Call webview.start() on main thread after this.
    """
    html_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "window.html")

    with open(html_path, "r") as f:
        html = f.read()

    # Inject real icon path as a file:// URL
    #icon_url = f"file://{icon_path}"
    #html = html.replace("__ICON_PATH__", icon_url)

    api = Api()

    win = webview.create_window(
        title            = "Arcn",
        html             = html,
        js_api           = api,
        width            = 750,
        height           = 550,
        frameless        = True,
        on_top           = True,
        background_color = "#0e0e0e",
        resizable        = False,
        hidden           = False,   # start hidden — menu bar click reveals it
    )

    api.set_window(win)
    return win, api