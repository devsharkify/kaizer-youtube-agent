# ============================================================
# KAIZER NEWS TELUGU — MODE 2 CONFIG
# ============================================================

import os

# APIs
HEYGEN_API_KEY     = os.getenv("HEYGEN_API_KEY", "sk_V2_hgu_kowntpjMBPx_YwifkgXDJLVNNOQBiqW4OQ79WfVCKExd")
ANTHROPIC_API_KEY  = os.getenv("ANTHROPIC_API_KEY", "")
YOUTUBE_STREAM_KEY = os.getenv("YOUTUBE_STREAM_KEY", "hw4v-196g-tj1s-apat-cr32")

# HeyGen avatar (Roku Digital — Digital Twin)
AVATAR_ID = os.getenv("AVATAR_ID", "4992180eef1647bbb182413ed0d0822c")

# Bulletin settings
STORIES_PER_BULLETIN = int(os.getenv("STORIES_PER_BULLETIN", "5"))
BULLETIN_INTERVAL_MIN = int(os.getenv("BULLETIN_INTERVAL_MIN", "30"))
SECONDS_PER_STORY = 20

# Canvas layout (960x540)
W, H = 960, 540
LX, LY, LW, LH = 22, 80, 457, 317   # left panel (images)
RX, RY, RW, RH = 481, 80, 457, 317  # right panel (avatar)

# YouTube RTMP
RTMP_URL = f"rtmp://a.rtmp.youtube.com/live2/{YOUTUBE_STREAM_KEY}"

# RSS feeds (only articles with images are selected)
RSS_FEEDS = [
    "https://rss2json.com/api.json?rss_url=https://feeds.feedburner.com/ndtvnews-india-news",
    "https://rss2json.com/api.json?rss_url=https://timesofindia.indiatimes.com/rssfeedstopstories.cms",
    "https://rss2json.com/api.json?rss_url=https://www.thehindu.com/feeder/default.rss",
    "https://rss2json.com/api.json?rss_url=https://indianexpress.com/feed/",
    "https://rss2json.com/api.json?rss_url=https://zeenews.india.com/rss/india-national-news.xml",
]
