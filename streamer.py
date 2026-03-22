# ============================================================
# STREAMER — FFmpeg → YouTube RTMP 24/7
# ============================================================

import subprocess, os, signal, logging, time
from config import RTMP_URL

log = logging.getLogger("streamer")
_proc = None

def start_stream(video_path: str):
    """Start looping video_path to YouTube RTMP. Non-blocking."""
    global _proc
    stop_stream()  # kill any existing
    
    cmd = [
        "ffmpeg", "-re",
        "-stream_loop", "-1",
        "-i", video_path,
        "-c:v", "libx264", "-preset", "veryfast",
        "-b:v", "2500k", "-maxrate", "2500k", "-bufsize", "5000k",
        "-g", "60", "-keyint_min", "60",
        "-c:a", "aac", "-b:a", "128k", "-ar", "44100",
        "-f", "flv",
        RTMP_URL
    ]
    log.info(f"Starting stream to YouTube: {RTMP_URL[:40]}...")
    _proc = subprocess.Popen(cmd)
    log.info(f"Stream PID: {_proc.pid}")

def swap_video(new_video_path: str):
    """
    Swap to new video without breaking the RTMP stream.
    Strategy: kill old ffmpeg, start new one instantly.
    YouTube allows brief reconnects on the same stream key.
    """
    log.info(f"Swapping to new video: {new_video_path}")
    start_stream(new_video_path)  # stops old, starts new

def stop_stream():
    """Stop the current FFmpeg stream process."""
    global _proc
    if _proc and _proc.poll() is None:
        log.info(f"Stopping stream PID {_proc.pid}")
        _proc.terminate()
        try:
            _proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            _proc.kill()
    _proc = None

def is_streaming() -> bool:
    return _proc is not None and _proc.poll() is None
