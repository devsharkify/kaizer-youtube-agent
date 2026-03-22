# ============================================================
# SCRIPT WRITER — Claude API writes Telugu bulletin
# ============================================================

import anthropic, logging
from config import ANTHROPIC_API_KEY

log = logging.getLogger("script_writer")

def write_telugu_script(stories: list[dict]) -> str:
    """Generate a Telugu news bulletin. Stories separated by [STORY_BREAK]."""
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    stories_text = "\n".join(
        f"{i+1}. {s['title']}" for i, s in enumerate(stories)
    )

    prompt = f"""You are Priya, a Telugu news anchor for Kaizer News Telugu.

Write a Telugu news bulletin for these {len(stories)} stories.

Stories:
{stories_text}

STRICT RULES:
- Start DIRECTLY with the first news story. NO greeting. NO "నమస్కారం".
- Each story: 2-3 Telugu sentences (~20 seconds when spoken).
- Between each story add exactly this on its own line: [STORY_BREAK]
- Telugu script ONLY. No English words.
- Do NOT include any greeting, intro, or sign-off.
- Output only the bulletin with [STORY_BREAK] markers. Nothing else.
"""

    log.info("Calling Claude for Telugu script...")
    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}]
    )
    script = resp.content[0].text.strip()
    log.info(f"Script: {len(script.split())} words, {script.count('[STORY_BREAK]')} breaks")
    return script
