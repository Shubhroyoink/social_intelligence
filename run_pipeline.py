import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import (
    create_database, save_posts, save_sentiments, save_trends,
    save_emotions, save_demographics, save_network_nodes, save_network_edges,
    save_narrative,
)


def collect_data(topic_query, telegram_channels=None, x_queries=None,
                 telegram_limit=100, x_limit=20):
    from collectors.telegram_collector import collect_telegram
    from collectors.x_collector import collect_x_search

    all_posts = []

    if telegram_channels:
        print(f"[Telegram] Collecting from {len(telegram_channels)} channels...")
        try:
            tg_posts = collect_telegram(telegram_channels, topic_query, limit_per_channel=telegram_limit)
            all_posts.extend(tg_posts)
            print(f"  -> {len(tg_posts)} Telegram posts")
        except Exception as e:
            print(f"  [WARN] Telegram collection failed: {e}")

    if x_queries:
        print(f"[X] Collecting for {len(x_queries)} queries...")
        for query in x_queries:
            try:
                x_posts = collect_x_search(query, topic_query, limit=x_limit)
                all_posts.extend(x_posts)
                print(f"  -> '{query}': {len(x_posts)} tweets")
            except Exception as e:
                print(f"  [WARN] X query '{query}' failed: {e}")

    return all_posts


def collect_youtube_data(topic_query, youtube_urls, youtube_limit=100):
    from collectors.youtube_collector import collect_youtube_comments

    all_posts = []
    print(f"[YouTube] Collecting from {len(youtube_urls)} videos...")

    for url in youtube_urls:
        try:
            yt_posts = collect_youtube_comments(url, topic_query, limit=youtube_limit)
            all_posts.extend(yt_posts)
            print(f"  -> {url[:50]}...: {len(yt_posts)} comments")
        except Exception as e:
            print(f"  [WARN] YouTube collection failed for {url}: {e}")

    return all_posts


def collect_youtube_topic_data(topic_query, max_videos=5, comments_per_video=100,
                               refresh=False, budget_units=2000):
    from collectors.youtube_collector import collect_youtube_topic
    return collect_youtube_topic(
        topic_query,
        max_videos=max_videos,
        comments_per_video=comments_per_video,
        refresh=refresh,
        budget_units=budget_units,
    )


def run(topic_query="AI Agents", telegram_channels=None, x_queries=None,
        youtube_urls=None, telegram_limit=100, x_limit=20, youtube_limit=100,
        youtube_search=True, yt_max_videos=5, yt_comments=100,
        yt_budget_units=2000, yt_refresh=False,
        do_collect=True, do_analyze=True, window_size_hours=24,
        skip_emotions=False, skip_demographics=False, skip_network=False,
        skip_narrative=False):
    create_database()

    if do_collect:
        raw = collect_data(topic_query, telegram_channels, x_queries, telegram_limit, x_limit)

        if youtube_urls:
            yt_raw = collect_youtube_data(topic_query, youtube_urls, youtube_limit)
            raw.extend(yt_raw)

        if youtube_search:
            print(f"[YouTube] Discovering up to {yt_max_videos} videos for "
                  f"topic '{topic_query}' (budget cap {yt_budget_units} units)...")
            try:
                yt_posts = collect_youtube_topic_data(
                    topic_query,
                    max_videos=yt_max_videos,
                    comments_per_video=yt_comments,
                    refresh=yt_refresh,
                    budget_units=yt_budget_units,
                )
                raw.extend(yt_posts)
                print(f"  -> {len(yt_posts)} YouTube comments via topic search")
            except RuntimeError as e:
                print(f"  [WARN] YouTube topic search skipped: {e}")

        from normalizer.normalizer import normalize_posts, dedupe
        normalized = normalize_posts(raw)
        normalized = dedupe(normalized, key="id")

        print(f"Normalized {len(normalized)} unique posts")
        save_posts(normalized)
        print("Saved posts to social.db")

        posts = normalized
    else:
        from database.db import get_posts
        posts = get_posts(topic_query=topic_query)
        print(f"Loaded {len(posts)} existing posts from DB")

    if not do_analyze:
        print("Analysis skipped. Done.")
        return posts

    sentiments = []
    emotions = []
    demographics = []
    network = None

    if posts:
        print("Running sentiment analysis...")
        from analytics.sentiment import analyze_posts
        sentiments = analyze_posts(posts)
        save_sentiments(sentiments)
        print(f"  Analyzed sentiment for {len(sentiments)} posts")

    print("Detecting trends...")
    from analytics.trends import detect_trends, rising_terms
    trends = detect_trends(posts, topic_query, window_size_hours=window_size_hours)
    if trends:
        save_trends(trends)
    print(f"  Saved {len(trends)} trend observations")

    hot = rising_terms(posts, window_size_hours=window_size_hours)
    print("\nCurrently rising terms:")
    for kw, freq in hot[:10]:
        print(f"   {kw}: {freq}")

    if not skip_emotions and posts:
        print("\nRunning emotion analysis...")
        from analytics.emotions import analyze_emotions
        emotions = analyze_emotions(posts)
        if emotions:
            save_emotions(emotions)
            print(f"  Analyzed emotions for {len(emotions)} posts")

    if not skip_demographics and posts:
        print("\nRunning demographic profiling...")
        from analytics.demographics import analyze_demographics
        demographics = analyze_demographics(posts)
        if demographics:
            save_demographics(demographics)
            print(f"  Profiled demographics for {len(demographics)} posts")

    if not skip_network and posts:
        print("\nBuilding network graph...")
        from analytics.network import analyze_network
        network = analyze_network(posts, topic_query, sentiments)
        if network["nodes"]:
            save_network_nodes(network["nodes"])
            save_network_edges(network["edges"])
            print(f"  Mapped {len(network['nodes'])} nodes, {len(network['edges'])} edges")
            print(f"  Identified {len(network['kols'])} key opinion leaders")

    if not skip_narrative and posts:
        print("\nGenerating narrative report...")
        from analytics.narrative import generate_narrative, write_report_file
        narrative = generate_narrative(
            posts, sentiments=sentiments, emotions=emotions,
            demographics=demographics, trends=trends, network=network,
            topic_query=topic_query,
        )
        if narrative:
            save_narrative(narrative)
            report_path = write_report_file(
                topic_query, narrative["report_markdown"], narrative["created_at"]
            )
            print(f"  Saved narrative report ({narrative['backend']} backend)")
            if narrative["model"]:
                print(f"    model: {narrative['model']}")
            print(f"    wrote file: {report_path}")
        else:
            print("  No posts to narrate; skipped")

    print("\nPipeline complete.")
    return posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Social Media Analytics Pipeline")
    parser.add_argument("--topic", default="AI Agents", help="Topic query to search")
    parser.add_argument("--channels", nargs="*", default=["@aipost", "@KDnuggets", "@theaiexecutive"],
                        help="Telegram channels to collect")
    parser.add_argument("--x-queries", nargs="*", default=["AI Agents"], help="X search queries")
    parser.add_argument("--youtube-urls", nargs="*", default=None,
                        help="YouTube video URLs to scrape comments from")
    parser.add_argument("--no-youtube-search", action="store_true",
                        help="Disable topic-based YouTube video discovery")
    parser.add_argument("--yt-max-videos", type=int, default=5,
                        help="Videos to discover per topic (search.list)")
    parser.add_argument("--yt-comments", type=int, default=100,
                        help="Max YouTube comments per video during discovery")
    parser.add_argument("--yt-budget-units", type=int, default=2000,
                        help="Per-run cap on estimated YouTube quota units")
    parser.add_argument("--yt-refresh", action="store_true",
                        help="Re-extract comments for already-cached videos")
    parser.add_argument("--tg-limit", type=int, default=100, help="Max Telegram posts per channel")
    parser.add_argument("--x-limit", type=int, default=20, help="Max X posts per query")
    parser.add_argument("--yt-limit", type=int, default=100, help="Max YouTube comments per video")
    parser.add_argument("--no-collect", action="store_true", help="Skip collection, use existing DB data")
    parser.add_argument("--no-analyze", action="store_true", help="Skip analysis, collect only")
    parser.add_argument("--window", type=int, default=24, help="Trend window size in hours")
    parser.add_argument("--skip-emotions", action="store_true", help="Skip emotion analysis")
    parser.add_argument("--skip-demographics", action="store_true", help="Skip demographic profiling")
    parser.add_argument("--skip-network", action="store_true", help="Skip network analysis")
    parser.add_argument("--skip-narrative", action="store_true", help="Skip narrative report generation")

    args = parser.parse_args()

    run(
        topic_query=args.topic,
        telegram_channels=args.channels,
        x_queries=args.x_queries,
        youtube_urls=args.youtube_urls,
        telegram_limit=args.tg_limit,
        x_limit=args.x_limit,
        youtube_limit=args.yt_limit,
        youtube_search=not args.no_youtube_search,
        yt_max_videos=args.yt_max_videos,
        yt_comments=args.yt_comments,
        yt_budget_units=args.yt_budget_units,
        yt_refresh=args.yt_refresh,
        do_collect=not args.no_collect,
        do_analyze=not args.no_analyze,
        window_size_hours=args.window,
        skip_emotions=args.skip_emotions,
        skip_demographics=args.skip_demographics,
        skip_network=args.skip_network,
        skip_narrative=args.skip_narrative,
    )
