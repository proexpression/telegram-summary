import feedparser
import requests
import schedule
import time

# ── Config ────────────────────────────────────────────────
RSS_URL         = "https://rsshub.app/telegram/channel/sternenko"
OPENROUTER_KEY  = "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"
TELEGRAM_TOKEN  = "8751921873:AAGI8gi8boQB9LhaQTBg6SGAuuAIQ-RViUE"
TELEGRAM_CHAT   = "304913194"
SEND_HOUR       = 19  # 7 PM
# ─────────────────────────────────────────────────────────


def fetch_posts():
    feed = feedparser.parse(RSS_URL)
    posts = []
    for entry in feed.entries[:20]:  # last 20 posts
        title   = entry.get("title", "")
        summary = entry.get("summary", entry.get("description", ""))
        posts.append(f"{title}\n{summary}")
    return "\n\n---\n\n".join(posts)


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
            "text": f"📰 *Daily Summary — Sternenko*\n\n{text}",
            "parse_mode": "Markdown",
        },
        timeout=10,
    ).raise_for_status()


def run_summary():
    print("Fetching posts...")
    posts = fetch_posts()
    if not posts:
        print("No posts found.")
        return
    print("Summarizing...")
    summary = summarize(posts)
    print("Sending to Telegram...")
    send_telegram(summary)
    print("Done!")


# Run once immediately on startup so you can test it
run_summary()

# Then schedule daily at 7 PM
schedule.every().day.at(f"{SEND_HOUR:02d}:00").do(run_summary)

print(f"Scheduler running — will send summary every day at {SEND_HOUR}:00")
while True:
    schedule.run_pending()
    time.sleep(60)
