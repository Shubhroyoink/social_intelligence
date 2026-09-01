import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import create_database, save_posts, save_sentiments, save_trends
from normalizer.normalizer import normalize_posts, dedupe


def collect_data(topic_query, telegram_channels=None, x_queries=None, telegram_limit=100, x_limit=20):
    """Run all collectors and return raw, unnormalized posts."""
    from collectors.telegram_collector import collect_telegram
    from collectors.x_collector import collect_x_search

    all_posts = []

    if telegram_channels:
        print(f"[1/3] Collecting Telegram from {len(telegram_channels)} channels...")
        try:
            tg_posts = collect_telegram(telegram_channels, topic_query, limit_per_channel=telegram_limit)
            all_posts.extend(tg_posts)
            print(f"      -> {len(tg_posts)} Telegram posts")
        except Exception as e:
            print(f"      [WARN] Telegram collection failed: {e}")

    if x_queries:
        print(f"[2/3] Collecting X for {len(x_queries)} queries...")
        from collectors.x_collector import collect_x_search
        for query in x_queries:
            try:
                x_posts = collect_x_search(query, topic_query, limit=x_limit)
                all_posts.extend(x_posts)
                print(f"      -> '{query}': {len(x_posts)} tweets")
            except Exception as e:
                print(f"      [WARN] X query '{query}' failed: {e}")

    return all_posts


def run(topic_query="AI Agents", telegram_channels=None, x_queries=None,
        telegram_limit=100, x_limit=20, do_collect=True, do_analyze=True,
        window_size_hours=24):
    """Full pipeline: collect -> normalize -> save -> analyze -> save results."""
    create_database()

    if do_collect:
        # [1] Collect
        raw = collect_data(topic_query, telegram_channels, x_queries, telegram_limit, x_limit)

        # [2] Normalize + dedupe
        normalized = normalize_posts(raw)
        normalized = dedupe(normalized, key="id")

        print(f"Normalized {len(normalized)} unique posts")

        # [3] Save to DB
        save_posts(normalized)
        print("Saved posts to social.db")

        posts = normalized
    else:
        # Load existing posts from DB
        from database.db import get_posts
        posts = get_posts(topic_query=topic_query)
        print(f"Loaded {len(posts)} existing posts from DB")

    if not do_analyze:
        print("Analysis skipped. Done.")
        return posts

    # [4] Sentiment analysis
    if posts:
        print("Running sentiment analysis...")
        from analytics.sentiment import analyze_posts
        sentiments = analyze_posts(posts)
        save_sentiments(sentiments)
        print(f"Analyzed sentiment for {len(sentiments)} posts")
    else:
        sentiments = []

    # [5] Trend detection
    print("Detecting trends...")
    from analytics.trends import detect_trends, rising_terms
    trends = detect_trends(posts, topic_query, window_size_hours=window_size_hours)
    if trends:
        save_trends(trends)
    print(f"Saved {len(trends)} trend observations across time windows")

    hot = rising_terms(posts, window_size_hours=window_size_hours)
    print("\nCurrently rising terms:")
    for kw, freq in hot[:10]:
        print(f"   {kw}: {freq}")

    return posts, sentiments, trends


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Social Media Analytics Pipeline")
    parser.add_argument("--topic", default="AI Agents", help="Topic query to search")
    parser.add_argument("--channels", nargs="*", default=["@aipost", "@KDnuggets", "@theaiexecutive"],
                        help="Telegram channels to collect")
    parser.add_argument("--x-queries", nargs="*", default=["AI Agents"], help="X search queries")
    parser.add_argument("--tg-limit", type=int, default=100, help="Max Telegram posts per channel")
    parser.add_argument("--x-limit", type=int, default=20, help="Max X posts per query")
    parser.add_argument("--no-collect", action="store_true", help="Skip collection, use existing DB data")
    parser.add_argument("--no-analyze", action="store_true", help="Skip analysis, collect only")
    parser.add_argument("--window", type=int, default=24, help="Trend window size in hours")

    args = parser.parse_args()

    run(
        topic_query=args.topic,
        telegram_channels=args.channels,
        x_queries=args.x_queries,
        telegram_limit=args.tg_limit,
        x_limit=args.x_limit,
        do_collect=not args.no_collect,
        do_analyze=not args.no_analyze,
        window_size_hours=args.window,
    )
