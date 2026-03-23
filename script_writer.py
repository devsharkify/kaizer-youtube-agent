import anthropic, logging
from config import ANTHROPIC_API_KEY, STORIES_PER_BULLETIN

log = logging.getLogger("script_writer")

def write_telugu_script(stories: list[dict]) -> str:
    client = anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)

    stories_text = "\n".join(
        f"{i+1}. {s['title']}" for i, s in enumerate(stories)
    )

    prompt = f"""You are Priya, Telugu news anchor for Kaizer News Telugu.

Write a SHORT Telugu bulletin for these {len(stories)} stories.

Stories:
{stories_text}

STRICT RULES:
- Start DIRECTLY with first news story. NO greeting. NO namaskaram.
- Each story: EXACTLY 2 Telugu sentences only. Keep it very short.
- Between each story put exactly: [STORY_BREAK]
- Telugu ONLY. No English.
- Total bulletin must be under 200 words.
- Output only the script. Nothing else.
"""

    log.info("Calling Claude...")
    resp = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=800,
        messages=[{"role": "user", "content": prompt}]
    )
    script = resp.content[0].text.strip()
    log.info(f"Script: {len(script.split())} words, {script.count('[STORY_BREAK]')} breaks")
    return script
