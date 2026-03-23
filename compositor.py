import subprocess, os, requests, logging, tempfile, re, json
from config import W, H, LX, LY, LW, LH, RX, RY, RW, RH, SECONDS_PER_STORY

log = logging.getLogger("compositor")

def download_image(url, path):
    try:
        r = requests.get(url, timeout=10, stream=True, headers={"User-Agent":"Mozilla/5.0"})
        with open(path,"wb") as f:
            for chunk in r.iter_content(8192): f.write(chunk)
        return os.path.getsize(path) > 1000
    except Exception as e:
        log.warning(f"Image download failed: {e}")
        return False

def make_canvas_card(story, idx, path):
    from PIL import Image, ImageDraw
    nc = Image.new("RGB",(LW,LH),(10,10,24))
    draw = ImageDraw.Draw(nc)
    draw.rectangle([(0,0),(LW,6)], fill=(204,0,0))
    title = (story.get("title") or f"Story {idx+1}")[:80]
    draw.text((10,20), title[:50], fill=(255,255,255))
    if len(title)>50: draw.text((10,42), title[50:], fill=(200,200,200))
    nc.save(path)

def build_story_images(stories, tmpdir):
    img_paths = []
    for i, story in enumerate(stories):
        path = os.path.join(tmpdir, f"story_{i}.jpg")
        ok = False
        if story.get("image"):
            ok = download_image(story["image"], path)
        if not ok:
            card = path.replace(".jpg",".png")
            make_canvas_card(story, i, card)
            path = card
        img_paths.append(path)
        log.info(f"  Story {i+1} image: {path}")
    return img_paths

def safe_drawtext(text):
    """Escape text for FFmpeg drawtext filter."""
    # Remove or replace all problematic chars
    text = text.replace("'", "").replace('"',"").replace("`","")
    text = text.replace(":", " -").replace("\\","").replace("%","")
    text = text.replace("[","(").replace("]",")")
    # Limit length
    return text[:300]

def composite_video(avatar_path, template_path, stories, script, logo_path, output_path):
    tmpdir = tempfile.mkdtemp()

    # 1. Story images
    img_paths = build_story_images(stories, tmpdir)

    # 2. Avatar duration
    probe = subprocess.run(
        ["ffprobe","-v","quiet","-print_format","json","-show_format",avatar_path],
        capture_output=True, text=True
    )
    av_dur = float(json.loads(probe.stdout)["format"]["duration"])
    log.info(f"Avatar duration: {av_dur:.1f}s")

    # 3. Build inputs
    n = len(stories)
    inputs = [
        "-stream_loop","-1","-i",template_path,  # 0: BG
        "-i",avatar_path,                          # 1: avatar
    ]
    for p in img_paths:
        inputs += ["-i", p]                        # 2..N+1
    inputs += ["-i", logo_path]                    # N+2
    logo_idx = n + 2

    # 4. Build safe ticker (Telugu titles from script, English as fallback)
    parts = script.split("[STORY_BREAK]")
    ticker_parts = []
    for i, s in enumerate(stories):
        # Try Telugu from script
        tel = parts[i].strip() if i < len(parts) else ""
        first = tel.split("।")[0].split(".")[0].strip()
        first = re.sub(r'[a-zA-Z0-9]','',first).strip()[:40]
        if len(first) > 5:
            ticker_parts.append(f"({i+1}) {first}")
        else:
            ticker_parts.append(f"({i+1}) {safe_drawtext(s['title'])}")
    ticker = " ** ".join(ticker_parts) + " ** Kaizer News Telugu ** "
    ticker_safe = safe_drawtext(ticker)

    # 5. Filter complex
    flt = []
    flt.append(f"[0:v]scale={W}:{H}[bg]")
    flt.append(f"[1:v]scale={RW}:{RH},chromakey=0x00c851:0.35:0.1[av_keyed]")
    flt.append(f"[{logo_idx}:v]scale=48:-1[logo]")
    flt.append(f"[bg][av_keyed]overlay={RX}:{RY}[with_av]")

    prev = "with_av"
    for i, img_path in enumerate(img_paths):
        idx = i + 2
        t0  = i * SECONDS_PER_STORY
        t1  = (i+1) * SECONDS_PER_STORY
        sc  = f"img{i}s"
        ov  = f"wi{i}"
        flt.append(f"[{idx}:v]scale={LW}:{LH}[{sc}]")
        flt.append(f"[{prev}][{sc}]overlay={LX}:{LY}:enable='between(t,{t0},{t1})'[{ov}]")
        prev = ov

    flt.append(f"[{prev}][logo]overlay={W-60}:8[wl]")

    # Ticker + branding using drawtext
    font_bold = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
    font_reg  = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"

    ticker_len = len(ticker_safe) * 8 + 100
    drawtext_chain = (
        f"[wl]"
        f"drawbox=x=0:y={H-52}:w={W}:h=52:color=black@0.9:t=fill,"
        f"drawbox=x=0:y={H-50}:w=165:h=48:color=0xcc0000:t=fill,"
        f"drawtext=text='BREAKING NEWS':fontcolor=white:fontsize=14"
        f":fontfile={font_bold}:x=8:y={H-26},"
        f"drawtext=text='{ticker_safe}   {ticker_safe}':fontcolor=white:fontsize=12"
        f":fontfile={font_reg}:x='mod(-t*60\\,{ticker_len})+168':y={H-20},"
        f"drawbox=x={W-180}:y=0:w=180:h=40:color=0xcc0000@0.9:t=fill,"
        f"drawtext=text='Kaizer News Telugu':fontcolor=white:fontsize=13"
        f":fontfile={font_bold}:x={W-175}:y=12"
        f"[final]"
    )
    flt.append(drawtext_chain)

    filter_complex = ";\n".join(flt)

    cmd = [
        "ffmpeg","-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map","[final]",
        "-map","1:a",
        "-c:v","libx264","-preset","veryfast","-crf","23",
        "-c:a","aac","-b:a","128k",
        "-t", str(av_dur),
        output_path
    ]

    log.info("Running FFmpeg compositor...")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"FFmpeg error: {result.stderr[-3000:]}")
        raise RuntimeError("FFmpeg compositor failed")

    log.info(f"✓ Final video: {output_path} ({os.path.getsize(output_path)//1024//1024}MB)")
    return output_path
