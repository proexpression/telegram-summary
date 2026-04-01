import requests
import schedule
import time
import xml.etree.ElementTree as ET

# ── Config ────────────────────────────────────────────────
RSS_URL         = "https://rsshub.app/telegram/channel/ssternenko"
OPENROUTER_KEY  = "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"
TELEGRAM_TOKEN  = "8751921873:AAGI8gi8boQB9LhaQTBg6SGAuuAIQ-RViUE"
TELEGRAM_CHAT   = "304913194"
SEND_HOUR       = 19  # 7 PM
# ─────────────────────────────────────────────────────────


def fetch_posts():
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(RSS_URL, headers=headers, timeout=15)
    r.raise_for_status()
    
    root = ET.fromstring(r.content)
    ns = {"content": "http://purl.org/rss/1.0/modules/content/"}
    
    posts = []
    for item in root.iter("item"):
        title = item.findtext("title") or ""
        desc  = item.findtext("description") or ""
        # strip HTML tags roughly
        import re
        desc = re.sub(r"<[^>]+>", "", desc).strip()
        posts.append(f"{title}\n{desc}".strip())
    
    print(f"Found {len(posts)} posts")
    return "\n\n---\n\n".join(posts[:20])


def summarize(posts_text):
    response = requests.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://railway.app",
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a helpful news assistant. "
                        "Summarize the following Telegram channel posts into a clear daily digest in English. "
                        "Group similar topics together. Use bullet points. "
                        "Highlight the most important news. Keep it under 300 words."
                    ),
                },
                {
                    "role": "user",
                    "content": f"Here are today's posts:\n\n{posts_text}",
                },
            ],
        },
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def send_telegram(text):
    requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT,
            "text": f"📰 *Daily Summary — Ssternenko*\n\n{text}",
            "parse_mode": "Markdown",
        },
        timeout=10,
    ).raise_for_status()


def run_summary():
    print("Fetching posts...")
    try:
        posts = fetch_posts()
        if not posts:
            print("No posts found.")
            return
        print("Summarizing...")
        summary = summarize(posts)
        print("Sending to Telegram...")
        send_telegram(summary)
        print("Done!")
    except Exception as e:
        print(f"Error: {e}")


# Run once immediately on startup
run_summary()

# Then schedule daily at 7 PM
schedule.every().day.at(f"{SEND_HOUR:02d}:00").do(run_summary)

print(f"Scheduler running — will send summary every day at {SEND_HOUR}:00")
while True:
    schedule.run_pending()
    time.sleep(60)
