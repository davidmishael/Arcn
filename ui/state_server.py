import threading
import time
import json
import subprocess
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

_state_ref     = None
_last_response = ""
_icon_path     = None
_last_intent   = ""
_last_raw_text = ""
_battery_pct   = None
_boot_time     = None

def set_last_intent(text: str):
    global _last_intent
    _last_intent = text

def set_last_raw_text(text: str):
    global _last_raw_text
    _last_raw_text = text

def set_battery(pct):
    global _battery_pct
    _battery_pct = pct

def set_boot_time(ts: float):
    global _boot_time
    _boot_time = ts

def set_state_source(state_obj):
    global _state_ref
    _state_ref = state_obj

def set_last_response(text: str):
    global _last_response
    _last_response = text

def set_icon_path(path: str):
    global _icon_path
    _icon_path = path


def _format_uptime() -> str:
    if _boot_time is None:
        return "—"
    elapsed = int(time.time() - _boot_time)
    hours, remainder = divmod(elapsed, 3600)
    minutes, seconds = divmod(remainder, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


# -------------------------
# Memory breakdown — App / Wired / Compressed,
# mirrors Activity Monitor's own accounting,
# plus Arcn's own process footprint.
# Module-level, not nested — called once per request.
# -------------------------
def _get_memory_breakdown():
    import psutil

    wired_gb = None
    compressed_gb = None
    app_gb = None

    try:
        page_size = os.sysconf("SC_PAGE_SIZE")
        result = subprocess.run(["vm_stat"], capture_output=True, text=True, timeout=2)

        wired_pages = None
        compressed_pages = None
        anonymous_pages = None
        purgeable_pages = None

        for line in result.stdout.splitlines():
            if "Pages wired down" in line:
                wired_pages = int(line.split(":")[1].strip().rstrip("."))
            elif "Pages occupied by compressor" in line:
                compressed_pages = int(line.split(":")[1].strip().rstrip("."))
            elif "Anonymous pages" in line:
                anonymous_pages = int(line.split(":")[1].strip().rstrip("."))
            elif "Pages purgeable" in line:
                purgeable_pages = int(line.split(":")[1].strip().rstrip("."))

        if wired_pages is not None:
            wired_gb = round((wired_pages * page_size) / (1024 ** 3), 2)

        if compressed_pages is not None:
            compressed_gb = round((compressed_pages * page_size) / (1024 ** 3), 2)

        # App Memory approximation — anonymous (non-file-backed) pages,
        # minus purgeable (instantly-reclaimable, not real app pressure).
        # This won't be byte-perfect against Activity Monitor (Apple doesn't
        # publish the exact formula) but stays self-consistent and in the
        # right ballpark, unlike mixing psutil's cross-platform "used" figure
        # with vm_stat's macOS-specific wired/compressed numbers.
        if anonymous_pages is not None and purgeable_pages is not None:
            app_pages = max(anonymous_pages - purgeable_pages, 0)
            app_gb = round((app_pages * page_size) / (1024 ** 3), 2)

    except Exception:
        pass

    # Self-consistent total — sum of the three parts we just derived,
    # rather than psutil's incompatible cross-platform "used" figure.
    sys_used_gb = None
    if wired_gb is not None and compressed_gb is not None and app_gb is not None:
        sys_used_gb = round(wired_gb + compressed_gb + app_gb, 1)

    arcn_gb = None
    try:
        arcn_gb = round(psutil.Process(os.getpid()).memory_info().rss / (1024 ** 3), 2)
    except Exception:
        pass

    return {
        "sys_used_gb"   : sys_used_gb,
        "wired_gb"      : wired_gb,
        "compressed_gb" : compressed_gb,
        "app_gb"        : app_gb,
        "arcn_gb"       : arcn_gb,
    }
class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/state":

            try:
                import psutil
                cpu_pct = psutil.cpu_percent(interval=None)
                mem = _get_memory_breakdown()
            except Exception:
                cpu_pct = None
                mem = {"sys_used_gb": None, "wired_gb": None, "compressed_gb": None, "app_gb": None, "arcn_gb": None}

            try:
                import db
                memory_turns = db.get_conversation_count()
            except Exception:
                memory_turns = None

            payload = json.dumps({
                "state"          : _state_ref.get() if _state_ref else "idle",
                "response"       : _last_response,
                "intent"         : _last_intent,
                "raw_text"       : _last_raw_text,
                "cpu"            : cpu_pct,
                "battery"        : _battery_pct,
                "uptime"         : _format_uptime(),
                "memory_turns"   : memory_turns,
                "ram_sys"        : mem["sys_used_gb"],
                "ram_wired"      : mem["wired_gb"],
                "ram_compressed" : mem["compressed_gb"],
                "ram_app"        : mem["app_gb"],
                "ram_arcn"       : mem["arcn_gb"],
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