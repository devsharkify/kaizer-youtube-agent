# ============================================================
# KAIZER NEWS TELUGU — MODE 2 MAIN
# ============================================================

import os, time, logging, schedule
from datetime import datetime
from config import BULLETIN_INTERVAL_MIN
from scraper       import fetch_stories
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

WORK_DIR    = "/tmp/kaizer"
ASSETS_DIR  = os.path.join(os.path.dirname(__file__), "assets")
LOGO_PATH   = os.path.join(ASSETS_DIR, "logo.png")
TEMPLATE    = os.path.join(ASSETS_DIR, "template.mp4")
CURRENT_MP4 = os.path.join(WORK_DIR, "current_bulletin.mp4")
NEXT_MP4    = os.path.join(WORK_DIR, "next_bulletin.mp4")

os.makedirs(WORK_DIR, exist_ok=True)

def bulletin_cycle():
    ts = datetime.now().strftime("%H:%M")
    log.info(f"═══ BULLETIN CYCLE {ts} ═══")
    try:
        # 1. News
        log.info("1. Fetching news...")
        stories = fetch_stories()
        if not stories:
            log.warning("No stories with images — skipping")
            return
        log.info(f"   Got {len(stories)} stories")

        # 2. Script
        log.info("2. Writing Telugu script...")
        script = write_telugu_script(stories)

        # 3. HeyGen
        log.info("3. Generating HeyGen video...")
        raw_av = os.path.join(WORK_DIR, "raw_avatar.mp4")
        generate_video(script, raw_av)

        # 4. Composite
        log.info("4. Compositing...")
        composite_video(
            avatar_path=raw_av,
            template_path=TEMPLATE,
            stories=stories,
            script=script,
            logo_path=LOGO_PATH,
            output_path=NEXT_MP4
        )

        # 5. Swap stream
        log.info("5. Swapping stream...")
        swap_video(NEXT_MP4)

        if os.path.exists(raw_av):
            os.remove(raw_av)

        log.info(f"✓ Bulletin {ts} live!")

    except Exception as e:
        log.error(f"Cycle failed: {e}", exc_info=True)

def main():
    log.info("╔══════════════════════════════════════╗")
    log.info("║  KAIZER NEWS TELUGU — MODE 2         ║")
    log.info("║  24/7 Auto YouTube Streaming          ║")
    log.info(f"║  Bulletin every {BULLETIN_INTERVAL_MIN} minutes            ║")
    log.info("╚══════════════════════════════════════╝")

    # Run first bulletin immediately
    bulletin_cycle()

    # Schedule
    schedule.every(BULLETIN_INTERVAL_MIN).minutes.do(bulletin_cycle)
    log.info(f"Next bulletin in {BULLETIN_INTERVAL_MIN} min")

    while True:
        schedule.run_pending()
        # Watchdog — only restart if we have a video file
        if not is_streaming():
            for mp4 in [NEXT_MP4, CURRENT_MP4]:
                if os.path.exists(mp4):
                    log.warning("Stream died — restarting...")
                    start_stream(mp4)
                    break
            else:
                log.info("Waiting for first bulletin to generate...")
        time.sleep(10)

if __name__ == "__main__":
    main()
