import os
import re
import time
import html
import requests
import schedule
import xml.etree.ElementTree as ET

RSS_URL = os.getenv("RSS_URL", "https://rsshub.app/telegram/channel/ssternenko")
OPENROUTER_KEY = os.getenv("OPENROUTER_KEY")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT = os.getenv("TELEGRAM_CHAT")
SEND_HOUR = int(os.getenv("SEND_HOUR", "19"))

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/rss+xml,application/xml,text/xml,text/html;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Cache-Control": "no-cache",
})

def strip_html(text):
    text = html.unescape(text or "")
    return re.sub(r"<[^>]+>", "", text).strip()

def fetch_posts():
    r = SESSION.get(RSS_URL, timeout=30, allow_redirects=True)
    if r.status_code != 200:
        raise RuntimeError(f"RSS fetch failed: {r.status_code} {r.text[:300]}")

    root = ET.fromstring(r.content)
    posts = []

    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        desc = strip_html(item.findtext("description") or "")
        if title or desc:
            posts.append(f"{title}\n{desc}".strip())

    return "\n\n---\n\n".join(posts[:20])

def summarize(posts_text):
    if not OPENROUTER_KEY:
        raise RuntimeError("OPENROUTER_KEY is missing")

    response = SESSION.post(
        "https://openrouter.ai/api/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {OPENROUTER_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://railway.app",
            "X-Title": "Telegram Daily Digest",
        },
        json={
            "model": "meta-llama/llama-3.1-8b-instruct:free",
            "messages": [
                {
                    "role": "system",
                    "content": (
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
        timeout=60,
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"].strip()

def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        raise RuntimeError("TELEGRAM_TOKEN or TELEGRAM_CHAT is missing")

    response = SESSION.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={
            "chat_id": TELEGRAM_CHAT,
            "text": f"📰 Daily Summary — Ssternenko\n\n{text}",
            "disable_web_page_preview": True,
        },
        timeout=20,
    )
    response.raise_for_status()

def run_summary():
    print("Fetching posts...")
    try:
        posts = fetch_posts()
        if not posts.strip():
            print("No posts found.")
            return

        print("Summarizing...")
        summary = summarize(posts)

        print("Sending to Telegram...")
        send_telegram(summary)

        print("Done!")
    except Exception as e:
        print(f"Error: {e}")

run_summary()
schedule.every().day.at(f"{SEND_HOUR:02d}:00").do(run_summary)

print(f"Scheduler running — will send summary every day at {SEND_HOUR:02d}:00")
while True:
    schedule.run_pending()
    time.sleep(60)
