# ============================================================
# HEYGEN — Generate avatar video via HeyGen Video API
# ============================================================

import requests, time, logging, os
from config import HEYGEN_API_KEY, AVATAR_ID

log = logging.getLogger("heygen")
BASE = "https://api.heygen.com"

def get_voice_id(voice_name: str = "Roku Digital") -> str:
    """Find voice ID by name."""
    r = requests.get(f"{BASE}/v2/voices", headers={"x-api-key": HEYGEN_API_KEY})
    voices = r.json().get("data", {}).get("voices", [])
    # Try exact match, then partial
    for v in voices:
        if v.get("name", "") == voice_name:
            return v["voice_id"]
    for v in voices:
        if voice_name.lower() in v.get("name", "").lower():
            return v["voice_id"]
    # Fallback: first Telugu voice
    for v in voices:
        if "telugu" in v.get("language", "").lower():
            return v["voice_id"]
    return voices[0]["voice_id"] if voices else ""

def generate_video(script: str, output_path: str) -> str:
    """Generate HeyGen avatar video. Returns local file path."""
    voice_id = get_voice_id()
    log.info(f"Voice ID: {voice_id}")

    # HeyGen max 5000 chars per request — trim if needed
    safe_script = script.replace("[STORY_BREAK]", " ... ").strip()[:4900]

    payload = {
        "video_inputs": [{
            "character": {
                "type": "avatar",
                "avatar_id": AVATAR_ID,
                "avatar_style": "normal"
            },
            "voice": {
                "type": "text",
                "input_text": safe_script,
                "voice_id": voice_id,
                "speed": 1.0
            },
            "background": {"type": "color", "value": "#00c851"}  # green for chroma key
        }],
        "dimension": {"width": 1280, "height": 720},
        "use_avatar_iv_model": False
    }

    log.info("Submitting to HeyGen...")
    r = requests.post(
        f"{BASE}/v2/video/generate",
        json=payload,
        headers={"x-api-key": HEYGEN_API_KEY, "Content-Type": "application/json"}
    )
    data = r.json()
    if data.get("error"):
        raise RuntimeError(f"HeyGen error: {data['error']}")
    
    video_id = data["data"]["video_id"]
    log.info(f"Video ID: {video_id} — polling...")

    # Poll until complete
    for attempt in range(180):  # 15 minutes max
        time.sleep(5)
        status_r = requests.get(
            f"{BASE}/v1/video_status.get?video_id={video_id}",
            headers={"x-api-key": HEYGEN_API_KEY}
        )
        status_data = status_r.json().get("data", {})
        status = status_data.get("status")
        log.info(f"  Status: {status} ({attempt*5}s)")
        
        if status == "completed":
            video_url = status_data["video_url"]
            log.info(f"✓ Video ready: {video_url[:60]}")
            # Download
            resp = requests.get(video_url, stream=True)
            with open(output_path, "wb") as f:
                for chunk in resp.iter_content(8192):
                    f.write(chunk)
            log.info(f"Downloaded: {output_path} ({os.path.getsize(output_path)//1024}KB)")
            return output_path
        elif status == "failed":
            raise RuntimeError(f"HeyGen render failed: {status_data.get('error')}")
    
    raise TimeoutError("HeyGen video generation timed out (15 min)")
