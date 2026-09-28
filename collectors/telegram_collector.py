from database.db import create_database, save_posts
from telethon.sync import TelegramClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

from normalizer.normalizer import dedupe, normalize_posts

load_dotenv()

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SESSION_FILE = os.path.join(PROJECT_ROOT, "session_name")

channels = ["@aipost",
            "@KDnuggets",
            "@theaiexecutive"]  # public channels on your topic


def _credentials():
    api_id = os.environ.get("TG_API_ID")
    api_hash = os.environ.get("TG_API_HASH")
    if not api_id or not api_hash:
        raise RuntimeError(
            "Telegram credentials missing. Set TG_API_ID and TG_API_HASH in "
            "your .env file (see .env.example)."
        )
    return api_id, api_hash


def collect_telegram(channels, topic_query, limit_per_channel=100):
    try:
        api_id, api_hash = _credentials()
    except Exception as e:
        print(f"[Telegram] Skipped: {e}")
        return []

    collected = []
    try:
        client = TelegramClient(SESSION_FILE, api_id, api_hash)
        client.connect()
        if not client.is_user_authorized():
            print("[Telegram] Session not authorized. Skipping interactive auth in background worker.")
            client.disconnect()
            return []

        for channel in channels:
            try:
                for msg in client.iter_messages(channel, limit=limit_per_channel):
                    if not msg.text:
                        continue
                    collected.append({
                        "id": f"{channel}_{msg.id}",
                        "platform": "telegram",
                        "author_id": str(msg.sender_id) if msg.sender_id else channel,
                        "author_handle": channel,
                        "text": msg.text,
                        "created_at": msg.date.isoformat() if msg.date else datetime.now(timezone.utc).isoformat(),
                        "collected_at": datetime.now(timezone.utc).isoformat(),
                        "parent_id": f"{channel}_{msg.reply_to_msg_id}" if msg.reply_to_msg_id else None,
                        "topic_query": topic_query,
                        "reactions": (
                            sum(r.count for r in msg.reactions.results)
                            if msg.reactions and msg.reactions.results
                            else 0
                        ),
                        "shares": msg.forwards or 0,
                        "replies": None,
                        "views": msg.views,
                    })
            except Exception as ce:
                print(f"[Telegram] Failed fetching channel {channel}: {ce}")
        client.disconnect()
    except Exception as ex:
        print(f"[Telegram] Warning: {ex}")

    return collected

if __name__ == "__main__":
    print("Starting Telegram collector...")

    create_database()

    data = collect_telegram(
        channels,
        topic_query="AI Agents",
        limit_per_channel=200
    )

    print(f"Collected {len(data)} messages")

    save_posts(dedupe(normalize_posts(data), key="id"))

    print("Saved messages to social.db")