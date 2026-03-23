# ============================================================
# KAIZER NEWS TELUGU — MODE 2 MAIN
# ============================================================

import os, time, logging, schedule, threading
from datetime import datetime, timedelta
from config import BULLETIN_INTERVAL_MIN
from scraper       import fetch_stories
from script_writer import write_telugu_script
from heygen        import generate_video
from compositor    import composite_video
from streamer      import start_stream, swap_video, stop_stream, is_streaming
import api as admin_api

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
NEXT_MP4    = os.path.join(WORK_DIR, "next_bulletin.mp4")
CURRENT_MP4 = os.path.join(WORK_DIR, "current_bulletin.mp4")

os.makedirs(WORK_DIR, exist_ok=True)

def set_status(status, **kwargs):
    admin_api.state["status"] = status
    admin_api.state.update(kwargs)
    admin_api.log_event(f"Status: {status}", "info")

def bulletin_cycle():
    ts = datetime.now().strftime("%H:%M")
    log.info(f"═══ BULLETIN CYCLE {ts} ═══")
    admin_api.log_event(f"Bulletin cycle started at {ts}")

    try:
        # 1. News
        set_status("fetching", current_story="Fetching news...")
        log.info("1. Fetching news...")
        stories = fetch_stories()
        if not stories:
            log.warning("No stories with images — skipping")
            admin_api.log_event("No stories found — skipping cycle", "warn")
            set_status("running")
            return
        admin_api.state["stories_count"] = len(stories)
        admin_api.state["current_story"] = stories[0]["title"]
        log.info(f"   Got {len(stories)} stories")
        admin_api.log_event(f"Got {len(stories)} stories with images")

        # 2. Script
        set_status("scripting", current_story="Writing Telugu script...")
        log.info("2. Writing Telugu script...")
        script = write_telugu_script(stories)
        admin_api.log_event(f"Script: {len(script.split())} words")

        # 3. HeyGen
        set_status("generating", current_story="Generating avatar video...")
        log.info("3. Generating HeyGen video...")
        raw_av = os.path.join(WORK_DIR, "raw_avatar.mp4")
        generate_video(script, raw_av)
        admin_api.log_event("Avatar video ready")

        # 4. Composite
        set_status("compositing", current_story="Compositing final video...")
        log.info("4. Compositing...")
        composite_video(
            avatar_path=raw_av,
            template_path=TEMPLATE,
            stories=stories,
            script=script,
            logo_path=LOGO_PATH,
            output_path=NEXT_MP4
        )
        admin_api.log_event("Composite done")

        # 5. Stream
        set_status("streaming", stream_live=True)
        log.info("5. Swapping stream...")
        swap_video(NEXT_MP4)

        if os.path.exists(raw_av):
            os.remove(raw_av)

        # Update state
        next_time = (datetime.now() + timedelta(minutes=BULLETIN_INTERVAL_MIN)).strftime("%H:%M")
        admin_api.state["last_bulletin"] = ts
        admin_api.state["next_bulletin"] = next_time
        admin_api.state["cycle_count"]  += 1
        admin_api.state["stream_live"]   = True
        admin_api.state["error"]         = ""
        set_status("streaming")
        log.info(f"✓ Bulletin {ts} live! Next at {next_time}")
        admin_api.log_event(f"✓ Bulletin live! Next at {next_time}")

    except Exception as e:
        log.error(f"Cycle failed: {e}", exc_info=True)
        admin_api.state["error"] = str(e)
        admin_api.log_event(f"ERROR: {e}", "error")
        set_status("error")

def main():
    log.info("╔══════════════════════════════════════╗")
    log.info("║  KAIZER NEWS TELUGU — MODE 2         ║")
    log.info("║  24/7 Auto YouTube Streaming          ║")
    log.info(f"║  Bulletin every {BULLETIN_INTERVAL_MIN} minutes            ║")
    log.info("╚══════════════════════════════════════╝")

    # Register API callbacks
    admin_api.set_callbacks(
        trigger_fn=bulletin_cycle,
        stop_fn=stop_stream,
        start_fn=lambda: start_stream(NEXT_MP4 if os.path.exists(NEXT_MP4) else CURRENT_MP4)
    )

    # Start admin API in background thread
    api_thread = threading.Thread(
        target=admin_api.run_api,
        kwargs={"port": int(os.getenv("PORT", 8080))},
        daemon=True
    )
    api_thread.start()
    log.info("Admin API running on port 8080")

    # Run first bulletin immediately
    bulletin_cycle()

    # Schedule
    schedule.every(BULLETIN_INTERVAL_MIN).minutes.do(bulletin_cycle)
    log.info(f"Next bulletin in {BULLETIN_INTERVAL_MIN} min")

    while True:
        schedule.run_pending()
        # Watchdog — only if video exists
        if not is_streaming():
            for mp4 in [NEXT_MP4, CURRENT_MP4]:
                if os.path.exists(mp4):
                    log.warning("Stream died — restarting...")
                    admin_api.log_event("Stream died — auto-restarting", "warn")
                    start_stream(mp4)
                    admin_api.state["stream_live"] = True
                    break
            else:
                log.info("Waiting for first bulletin...")
        time.sleep(10)

if __name__ == "__main__":
    main()
