from database.db import create_database, save_posts
from telethon.sync import TelegramClient
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

api_id = os.environ["TG_API_ID"]       # get from my.telegram.org
api_hash = os.environ["TG_API_HASH"]

channels = ["@aipost",
            "@KDnuggets",
            "@theaiexecutive"]  # public channels on your topic

def collect_telegram(channels, topic_query, limit_per_channel=200):
    collected = []
    with TelegramClient("session_name", api_id, api_hash) as client:
        for channel in channels:
            for msg in client.iter_messages(channel, limit=limit_per_channel):
                if not msg.text:
                    continue
                collected.append({
                    "id": f"{channel}_{msg.id}",
                    "platform": "telegram",
                    "author_id": str(msg.sender_id) if msg.sender_id else channel,
                    "author_handle": channel,
                    "text": msg.text,
                    "created_at": msg.date.isoformat(),
                    "collected_at": datetime.now(timezone.utc).isoformat(),
                    "parent_id": f"{channel}_{msg.reply_to_msg_id}" if msg.reply_to_msg_id else None,
                    "topic_query": topic_query,
                    "reactions": (
                        sum(r.count for r in msg.reactions.results)
                        if msg.reactions and msg.reactions.results
                        else 0
                    ),
                    "shares": msg.forwards or 0,
                    "replies": None,  # Telethon doesn't give reply counts directly; leave null
                    "views": msg.views,
                    "raw_json": str(msg.to_dict())
                })
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

    save_posts(data)

    print("Saved messages to social.db")