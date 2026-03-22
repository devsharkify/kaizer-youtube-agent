# ============================================================
# COMPOSITOR — FFmpeg: avatar + images + template → final MP4
# ============================================================

import subprocess, os, requests, logging, tempfile, re
from PIL import Image
import numpy as np
from config import W, H, LX, LY, LW, LH, RX, RY, RW, RH, SECONDS_PER_STORY

log = logging.getLogger("compositor")

def download_image(url: str, path: str) -> bool:
    """Download image to path. Returns True on success."""
    try:
        r = requests.get(url, timeout=10, stream=True)
        with open(path, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        return os.path.getsize(path) > 1000
    except Exception as e:
        log.warning(f"Image download failed: {e}")
        return False

def make_canvas_card(story: dict, idx: int, path: str):
    """Generate a dark news card as fallback image."""
    from PIL import Image, ImageDraw
    nc = Image.new("RGB", (LW, LH), (10, 10, 24))
    draw = ImageDraw.Draw(nc)
    draw.rectangle([(0, 0), (LW, 6)], fill=(204, 0, 0))
    # Wrap title text
    title = (story.get("title") or f"Story {idx+1}")[:100]
    draw.text((10, 20), title[:60], fill=(255, 255, 255))
    if len(title) > 60:
        draw.text((10, 42), title[60:120], fill=(255, 255, 255))
    nc.save(path)

def chroma_key_avatar(avatar_path: str, output_path: str):
    """Remove green background from avatar video using FFmpeg."""
    log.info("Applying chroma key to avatar...")
    cmd = [
        "ffmpeg", "-y", "-i", avatar_path,
        "-vf", "colorkey=0x00c851:0.35:0.1",
        "-c:v", "png", "-an", output_path
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    log.info(f"Chroma keyed: {output_path}")

def build_story_image_list(stories: list[dict], tmpdir: str) -> list[str]:
    """Download story images (or generate fallback cards)."""
    img_paths = []
    for i, story in enumerate(stories):
        path = os.path.join(tmpdir, f"story_{i}.jpg")
        ok = False
        if story.get("image"):
            ok = download_image(story["image"], path)
        if not ok:
            # Try Pollinations AI
            q = re.sub(r'[^\x20-\x7E]', ' ', story.get("title", "news")).strip()
            q = ' '.join(q.split()[:5])
            url = f"https://image.pollinations.ai/prompt/news+photo+{requests.utils.quote(q)}+india+photorealistic?width={LW}&height={LH}&nologo=true&seed={i}"
            ok = download_image(url, path)
        if not ok:
            # Canvas card fallback
            card_path = path.replace(".jpg", ".png")
            make_canvas_card(story, i, card_path)
            path = card_path
        img_paths.append(path)
        log.info(f"  Story {i+1} image: {path}")
    return img_paths

def composite_video(
    avatar_path: str,
    template_path: str,
    stories: list[dict],
    script: str,
    logo_path: str,
    output_path: str
) -> str:
    """
    Full compositor:
    - Background template (loops)
    - Avatar chroma keyed → RIGHT panel
    - Story images → LEFT panel (switches every SECONDS_PER_STORY)
    - Kaizer logo → top right
    - Telugu ticker → bottom
    Returns path to final MP4
    """
    import tempfile
    tmpdir = tempfile.mkdtemp()

    # 1. Download story images
    img_paths = build_story_image_list(stories, tmpdir)

    # 2. Get avatar duration
    probe = subprocess.run(
        ["ffprobe", "-v", "quiet", "-print_format", "json", "-show_format", avatar_path],
        capture_output=True, text=True
    )
    import json
    av_duration = float(json.loads(probe.stdout)["format"]["duration"])
    log.info(f"Avatar duration: {av_duration:.1f}s")

    # 3. Build FFmpeg filter_complex
    # Inputs: template(0), avatar(1), story_imgs(2..N+1), logo(N+2)
    n = len(stories)
    inputs = [
        "-stream_loop", "-1", "-i", template_path,  # 0: BG template loops
        "-i", avatar_path,                            # 1: avatar
    ]
    for p in img_paths:
        inputs += ["-i", p]                           # 2..N+1: story images
    inputs += ["-i", logo_path]                       # N+2: logo

    # Build ticker text (Telugu stories)
    ticker_parts = []
    for i, s in enumerate(stories):
        ticker_parts.append(f"({i+1}) {s['title']}")
    ticker = " ★★ ".join(ticker_parts) + " ★★ కైజర్ న్యూస్ తెలుగు ★★ "

    # Escape special chars for FFmpeg drawtext
    def esc(t):
        return t.replace("'", "\\'").replace(":", "\\:").replace("\\", "\\\\")

    # Blue strip text from script
    script_lines = [l.strip() for l in script.replace("[STORY_BREAK]", "\n").split("\n") if len(l.strip()) > 5]
    greet_re = re.compile(r'నమస్కారం|Kaizer News|నేను Priya', re.I)

    def get_blue_text(story_idx):
        lines = script.split("[STORY_BREAK]")
        if story_idx < len(lines):
            sents = [l.strip() for l in lines[story_idx].split('।') if len(l.strip()) > 4 and not greet_re.search(l)]
            if sents:
                return re.sub(r'[a-zA-Z0-9]', '', sents[0]).strip()[:30]
        return stories[story_idx].get("title", "")[:30] if story_idx < len(stories) else ""

    # FFmpeg filter_complex
    logo_w = 48
    logo_h = 48  # will be auto-proportioned

    filter_lines = []

    # Scale BG template to canvas
    filter_lines.append(f"[0:v]scale={W}:{H}[bg]")

    # Scale avatar to right panel size, apply chromakey
    filter_lines.append(
        f"[1:v]scale={RW}:{RH},chromakey=0x00c851:0.35:0.1[av_keyed]"
    )

    # Scale logo
    logo_idx = n + 2
    filter_lines.append(f"[{logo_idx}:v]scale={logo_w}:-1[logo]")

    # Overlay BG + avatar (right panel position)
    filter_lines.append(f"[bg][av_keyed]overlay={RX}:{RY}[with_av]")

    # Story images: overlay LEFT panel with time-based switching
    # Use enable='between(t,start,end)' for each image
    prev = "[with_av]"
    for i, img_path in enumerate(img_paths):
        img_input_idx = i + 2
        t_start = i * SECONDS_PER_STORY
        t_end   = (i + 1) * SECONDS_PER_STORY
        scaled   = f"img{i}_scaled"
        overlaid = f"with_img{i}"
        filter_lines.append(f"[{img_input_idx}:v]scale={LW}:{LH}[{scaled}]")
        filter_lines.append(
            f"[{prev}][{scaled}]overlay={LX}:{LY}:enable='between(t,{t_start},{t_end})'[{overlaid}]"
        )
        prev = overlaid

    # Overlay logo top right
    filter_lines.append(f"[{prev}][logo]overlay={W-logo_w-12}:8[with_logo]")

    # Breaking news bar
    filter_lines.append(
        f"[with_logo]drawbox=x=0:y={H-52}:w={W}:h=52:color=black@0.9:t=fill,"
        f"drawbox=x=0:y={H-50}:w=165:h=48:color=0xcc0000:t=fill,"
        f"drawtext=text='BREAKING NEWS':fontcolor=white:fontsize=14:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:x=8:y={H-26},"
        f"drawtext=text='{esc(ticker)}   {esc(ticker)}':fontcolor=white:fontsize=12:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:x='mod(-t*80\\,{len(ticker)*8})+168':y={H-20}"
        f"[final]"
    )

    filter_complex = ";\n".join(filter_lines)

    # FFmpeg command
    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[final]",
        "-map", "1:a",           # audio from avatar
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-c:a", "aac", "-b:a", "128k",
        "-t", str(av_duration),  # trim to avatar length
        output_path
    ]

    log.info("Running FFmpeg compositor...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"FFmpeg error: {result.stderr[-2000:]}")
        raise RuntimeError("FFmpeg compositor failed")

    log.info(f"✓ Final video: {output_path} ({os.path.getsize(output_path)//1024//1024}MB)")
    return output_path
