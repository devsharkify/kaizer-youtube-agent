import requests, time, logging, os
from config import HEYGEN_API_KEY, AVATAR_ID

log = logging.getLogger("heygen")
BASE = "https://api.heygen.com"

def get_voice_id() -> str:
    r = requests.get(f"{BASE}/v2/voices", headers={"x-api-key": HEYGEN_API_KEY}, timeout=15)
    voices = r.json().get("data", {}).get("voices", [])
    for v in voices:
        if "roku" in v.get("name","").lower(): return v["voice_id"]
    for v in voices:
        if "telugu" in v.get("language","").lower(): return v["voice_id"]
    return voices[0]["voice_id"] if voices else ""

def generate_video(script: str, output_path: str) -> str:
    voice_id = get_voice_id()
    log.info(f"Voice: {voice_id}")

    # Strip STORY_BREAK markers, keep pauses
    safe = script.replace("[STORY_BREAK]", " ... ").strip()
    # Hard limit 2000 chars for fast generation (~2 min video max)
    if len(safe) > 2000:
        safe = safe[:2000]
        log.warning("Script truncated to 2000 chars for speed")

    payload = {
        "video_inputs": [{
            "character": {"type":"avatar","avatar_id":AVATAR_ID,"avatar_style":"normal"},
            "voice":     {"type":"text","input_text":safe,"voice_id":voice_id,"speed":1.0},
            "background":{"type":"color","value":"#00c851"}
        }],
        "dimension": {"width":1280,"height":720},
        "use_avatar_iv_model": False
    }

    log.info("Submitting to HeyGen...")
    r = requests.post(f"{BASE}/v2/video/generate", json=payload,
        headers={"x-api-key":HEYGEN_API_KEY,"Content-Type":"application/json"}, timeout=30)
    data = r.json()
    if data.get("error"):
        raise RuntimeError(f"HeyGen error: {data['error']}")

    video_id = data["data"]["video_id"]
    log.info(f"Video ID: {video_id} — polling...")

    # Poll every 10s, max 20 minutes
    for attempt in range(120):
        time.sleep(10)
        sr = requests.get(f"{BASE}/v1/video_status.get?video_id={video_id}",
            headers={"x-api-key":HEYGEN_API_KEY}, timeout=15)
        sd = sr.json().get("data", {})
        status = sd.get("status")
        log.info(f"  Status: {status} ({(attempt+1)*10}s)")

        if status == "completed":
            url = sd["video_url"]
            log.info(f"✓ Video ready: {url[:60]}")
            resp = requests.get(url, stream=True, timeout=60)
            with open(output_path,"wb") as f:
                for chunk in resp.iter_content(8192): f.write(chunk)
            log.info(f"Downloaded: {output_path} ({os.path.getsize(output_path)//1024}KB)")
            return output_path
        elif status == "failed":
            raise RuntimeError(f"HeyGen failed: {sd.get('error')}")

    raise TimeoutError("HeyGen timed out after 20 min")
