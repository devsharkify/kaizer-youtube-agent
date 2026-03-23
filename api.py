# ============================================================
# KAIZER NEWS TELUGU — Admin API (Flask)
# Runs alongside main.py on Railway
# ============================================================

from flask import Flask, jsonify, request
from zoneinfo import ZoneInfo
IST = ZoneInfo('Asia/Kolkata')
from flask_cors import CORS
import threading, os, logging

app = Flask(__name__)
CORS(app)  # Allow dashboard to call from any origin

# Shared state (set by main.py)
state = {
    "status": "starting",          # starting | running | generating | streaming | stopped
    "current_story": "",
    "stories_count": 0,
    "last_bulletin": "",
    "next_bulletin": "",
    "stream_live": False,
    "logs": [],
    "cycle_count": 0,
    "error": "",
}

def log_event(msg, level="info"):
    import datetime
    entry = {"time": datetime.datetime.now(IST).strftime("%H:%M:%S IST"), "msg": msg, "level": level}
    state["logs"].insert(0, entry)
    state["logs"] = state["logs"][:100]  # keep last 100

# Callbacks to be set by main.py
_trigger_bulletin = None
_stop_stream = None
_start_stream = None

def set_callbacks(trigger_fn, stop_fn, start_fn):
    global _trigger_bulletin, _stop_stream, _start_stream
    _trigger_bulletin = trigger_fn
    _stop_stream = stop_fn
    _start_stream = start_fn

# ─── Routes ───────────────────────────────────────────────
@app.route("/", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "Kaizer News Admin API"})

@app.route("/status", methods=["GET"])
def get_status():
    return jsonify(state)

@app.route("/trigger", methods=["POST"])
def trigger():
    """Manually trigger a new bulletin now."""
    if _trigger_bulletin:
        threading.Thread(target=_trigger_bulletin, daemon=True).start()
        log_event("Manual bulletin triggered", "info")
        return jsonify({"ok": True, "msg": "Bulletin triggered"})
    return jsonify({"ok": False, "msg": "Not ready"}), 503

@app.route("/stop", methods=["POST"])
def stop():
    """Stop the YouTube stream."""
    if _stop_stream:
        _stop_stream()
        state["stream_live"] = False
        log_event("Stream stopped by admin", "warn")
        return jsonify({"ok": True, "msg": "Stream stopped"})
    return jsonify({"ok": False, "msg": "Not ready"}), 503

@app.route("/start", methods=["POST"])
def start():
    """Restart the YouTube stream."""
    if _start_stream:
        _start_stream()
        state["stream_live"] = True
        log_event("Stream started by admin", "info")
        return jsonify({"ok": True, "msg": "Stream started"})
    return jsonify({"ok": False, "msg": "Not ready"}), 503

@app.route("/logs", methods=["GET"])
def get_logs():
    return jsonify(state["logs"])

def run_api(port=8080):
    """Run Flask in a background thread."""
    log = logging.getLogger("api")
    log.info(f"Admin API starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
