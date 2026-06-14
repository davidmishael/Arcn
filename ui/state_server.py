import threading
import json
from http.server import HTTPServer, BaseHTTPRequestHandler

_state_ref     = None
_last_response = ""
_icon_path     = None
_last_intent = ""

def set_last_intent(text: str):
    global _last_intent
    _last_intent = text

def set_state_source(state_obj):
    global _state_ref
    _state_ref = state_obj

def set_last_response(text: str):
    global _last_response
    _last_response = text

def set_icon_path(path: str):
    global _icon_path
    _icon_path = path

class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/state":
            payload = json.dumps({
                "state":    _state_ref.get() if _state_ref else "idle",
                "response": _last_response,
                "intent": _last_intent
            }).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(payload)

        elif self.path == "/icon":
            if _icon_path is None:
                self.send_response(404)
                self.end_headers()
                return
            with open(_icon_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "image/png")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, *args):
        pass

def start(port=7373):
    server = HTTPServer(("127.0.0.1", port), _Handler)
    t = threading.Thread(target=server.serve_forever, daemon=True)
    t.start()