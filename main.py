# ============================================================
# KAIZER NEWS TELUGU — MODE 2 MAIN
# Full auto pipeline: RSS → Claude → HeyGen → Compositor → YouTube
# Runs every 30 minutes, streams 24/7
# ============================================================

import os, time, logging, schedule, glob
from datetime import datetime
from config import BULLETIN_INTERVAL_MIN, STORIES_PER_BULLETIN
from scraper      import fetch_stories
from script_writer import write_telugu_script
from heygen        import generate_video
from compositor    import composite_video
from streamer      import start_stream, swap_video, is_streaming

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("main")

WORK_DIR   = "/tmp/kaizer"
LOGO_PATH  = os.path.join(os.path.dirname(__file__), "assets/logo.png")
TEMPLATE   = os.path.join(os.path.dirname(__file__), "assets/template.mp4")
CURRENT_MP4 = os.path.join(WORK_DIR, "current_bulletin.mp4")
NEXT_MP4    = os.path.join(WORK_DIR, "next_bulletin.mp4")

os.makedirs(WORK_DIR, exist_ok=True)

def bulletin_cycle():
    """One full bulletin: scrape → script → generate → composite → swap."""
    ts = datetime.now().strftime("%H:%M")
    log.info(f"═══ BULLETIN CYCLE {ts} ═══")

    try:
        # Step 1: Fetch news
        log.info("1. Fetching news...")
        stories = fetch_stories()
        if not stories:
            log.warning("No stories with images found — skipping cycle")
            return
        log.info(f"   Got {len(stories)} stories")

        # Step 2: Write Telugu script
        log.info("2. Writing Telugu script...")
        script = write_telugu_script(stories)

        # Step 3: Generate HeyGen avatar video
        log.info("3. Generating HeyGen avatar video...")
        raw_av = os.path.join(WORK_DIR, "raw_avatar.mp4")
        generate_video(script, raw_av)

        # Step 4: Composite final video
        log.info("4. Compositing final video...")
        composite_video(
            avatar_path=raw_av,
            template_path=TEMPLATE,
            stories=stories,
            script=script,
            logo_path=LOGO_PATH,
            output_path=NEXT_MP4
        )

        # Step 5: Swap stream
        log.info("5. Swapping stream to new bulletin...")
        swap_video(NEXT_MP4)

        # Cleanup old raw avatar
        if os.path.exists(raw_av):
            os.remove(raw_av)

        log.info(f"✓ Bulletin {ts} live on YouTube!")

    except Exception as e:
        log.error(f"Cycle failed: {e}", exc_info=True)
        # Keep streaming current video — don't interrupt

def main():
    log.info("╔══════════════════════════════════════╗")
    log.info("║  KAIZER NEWS TELUGU — MODE 2         ║")
    log.info("║  24/7 Auto YouTube Streaming          ║")
    log.info(f"║  Bulletin every {BULLETIN_INTERVAL_MIN} minutes            ║")
    log.info("╚══════════════════════════════════════╝")

    # Run first bulletin immediately
    bulletin_cycle()

    # If stream not up yet (first run failed), try to stream whatever exists
    if not is_streaming() and os.path.exists(NEXT_MP4):
        start_stream(NEXT_MP4)

    # Schedule subsequent bulletins
    schedule.every(BULLETIN_INTERVAL_MIN).minutes.do(bulletin_cycle)

    log.info(f"Scheduler running — next bulletin in {BULLETIN_INTERVAL_MIN} min")
    while True:
        schedule.run_pending()
        # Watchdog: restart stream if it died
        if not is_streaming():
            log.warning("Stream died — restarting...")
            for mp4 in [CURRENT_MP4, NEXT_MP4]:
                if os.path.exists(mp4):
                    start_stream(mp4)
                    break
        time.sleep(10)

if __name__ == "__main__":
    main()
