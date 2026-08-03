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