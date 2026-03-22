# Kaizer News Telugu — Mode 2 (Server Auto Pipeline)

Fully automated 24/7 YouTube live stream. No human intervention needed.

## How it works

```
Every 30 minutes:
  1. RSS feeds → fetch articles WITH images only
  2. Claude API → write Telugu script (5 stories, [STORY_BREAK] separated)
  3. HeyGen API → generate avatar video (Roku Digital, green background)
  4. FFmpeg compositor:
       - Studio template (loops as background)
       - Avatar chroma keyed → RIGHT panel
       - Story images → LEFT panel (switches every 20s)
       - Kaizer logo → top right
       - Telugu ticker → bottom
  5. FFmpeg → swap bulletin → YouTube RTMP (24/7, unbroken)
```

## Setup

### 1. Add assets
```
assets/
  logo.png      ← Kaizer News logo (transparent PNG)
  template.mp4  ← Studio background template (loops)
```

### 2. Deploy to Railway
1. Push to GitHub
2. Connect Railway to repo
3. Set environment variables (see .env.example)
4. Deploy — Railway runs `python main.py`

### 3. Environment Variables
| Variable | Value |
|---|---|
| `HEYGEN_API_KEY` | Your HeyGen API key |
| `ANTHROPIC_API_KEY` | Your Claude API key |
| `YOUTUBE_STREAM_KEY` | YouTube live stream key |
| `AVATAR_ID` | HeyGen avatar ID (Roku Digital) |
| `STORIES_PER_BULLETIN` | 5 (default) |
| `BULLETIN_INTERVAL_MIN` | 30 (default) |

## Mode 1 vs Mode 2

| | Mode 1 | Mode 2 |
|---|---|---|
| Trigger | Manual (click buttons) | Automatic (every 30 min) |
| Runs on | Browser (HTML file) | Railway server |
| YouTube | Download + upload manually | Streams directly via RTMP |
| Monitoring | Watch in browser | Railway logs |
