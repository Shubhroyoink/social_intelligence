import argparse
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from database.db import (
    create_database, save_posts, save_sentiments, save_trends,
    save_emotions, save_demographics, save_network_nodes, save_network_edges,
    save_narrative, get_posts, get_sentiments, get_emotions,
    get_demographics, get_trends, get_network_nodes, get_network_edges,
)


def collect_data(topic_query, telegram_channels=None, x_queries=None,
                 telegram_limit=100, x_max_profiles=3, x_max_pages=1,
                 x_budget_credits=4, x_tweets_per_page=100,
                 x_include_replies=True, x_refresh=False, x_dry_run=False,
                 x_require_topic=True, x_allow_promo=False, notify_fn=None):
    from collectors.telegram_collector import collect_telegram
    from collectors.x_collector import (
        XCreditsExceededError, collect_x_for_topic, plan_credit_cost,
    )

    all_posts = []

    if telegram_channels:
        if notify_fn:
            notify_fn("Collecting Telegram", 12, f"Collecting from {len(telegram_channels)} Telegram channels...")
        print(f"[Telegram] Collecting from {len(telegram_channels)} channels...")
        try:
            tg_posts = collect_telegram(telegram_channels, topic_query, limit_per_channel=telegram_limit)
            all_posts.extend(tg_posts)
            print(f"  -> {len(tg_posts)} Telegram posts")
        except Exception as e:
            print(f"  [WARN] Telegram collection failed: {e}")

    effective_x_queries = x_queries if x_queries is not None else [topic_query]
    if effective_x_queries:
        if notify_fn:
            notify_fn("Collecting Twitter/X", 20, f"Collecting tweets for {len(effective_x_queries)} queries via SocialFetch...")
        planned = plan_credit_cost(
            x_max_profiles, x_max_pages, discovery_queries=len(effective_x_queries)
        )
        print(f"[X] {len(effective_x_queries)} discovery quer(y/ies) x (1 credit + "
              f"{x_max_profiles} profile(s) x {x_max_pages} page(s)) "
              f"= {planned} credit(s)")

        # 0 is a real budget (block everything), so only None disables the cap.
        if x_budget_credits is not None and planned > x_budget_credits:
            print(f"  [WARN] Plan of {planned} credits exceeds the budget of "
                  f"{x_budget_credits}; skipping X collection.")
            effective_x_queries = []

        for query in effective_x_queries:
            try:
                x_posts = collect_x_for_topic(
                    topic_query,
                    query=query,
                    max_profiles=x_max_profiles,
                    max_pages=x_max_pages,
                    budget_credits=None,  # already checked for the whole run
                    tweets_per_page=x_tweets_per_page,
                    include_replies=x_include_replies,
                    refresh=x_refresh,
                    dry_run=x_dry_run,
                    require_topic=x_require_topic,
                    allow_promo=x_allow_promo,
                )
                all_posts.extend(x_posts)
                print(f"  -> '{query}': {len(x_posts)} tweets")
            except XCreditsExceededError as e:
                print(f"  [WARN] X collection stopped: {e}")
                break
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
        youtube_urls=None, telegram_limit=100, youtube_limit=100,
        x_max_profiles=3, x_max_pages=1, x_budget_credits=4,
        x_tweets_per_page=100,         x_include_replies=True, x_refresh=False,
        x_dry_run=False, x_require_topic=True, x_allow_promo=False,
        youtube_search=True, yt_max_videos=5, yt_comments=100,
        yt_budget_units=2000, yt_refresh=False,
        do_collect=True, do_analyze=True, window_size_hours=24,
        skip_emotions=False, skip_demographics=False, skip_network=False,
        skip_narrative=False, progress_callback=None):
    
    def _notify(step, pct, msg):
        if progress_callback and callable(progress_callback):
            try:
                progress_callback(step, pct, msg)
            except Exception:
                pass

    _notify("Initializing", 5, f"Initializing pipeline for topic '{topic_query}'")
    create_database()

    if do_collect:
        raw = collect_data(
            topic_query=topic_query,
            telegram_channels=telegram_channels,
            x_queries=x_queries,
            telegram_limit=telegram_limit,
            x_max_profiles=x_max_profiles,
            x_max_pages=x_max_pages,
            x_budget_credits=x_budget_credits,
            x_tweets_per_page=x_tweets_per_page,
            x_include_replies=x_include_replies,
            x_refresh=x_refresh,
            x_dry_run=x_dry_run,
            x_require_topic=x_require_topic,
            x_allow_promo=x_allow_promo,
            notify_fn=_notify,
        )

        if youtube_urls:
            _notify("Collecting YouTube", 25, f"Fetching comments from {len(youtube_urls)} YouTube video(s)...")
            yt_raw = collect_youtube_data(topic_query, youtube_urls, youtube_limit)
            raw.extend(yt_raw)

        if youtube_search:
            _notify("Discovering YouTube", 30, f"Discovering YouTube videos for '{topic_query}'...")
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

        _notify("Normalizing Data", 40, f"Normalizing and deduplicating {len(raw)} gathered posts...")
        from normalizer.normalizer import normalize_posts, dedupe
        normalized = normalize_posts(raw)
        normalized = dedupe(normalized, key="id")

        print(f"Normalized {len(normalized)} unique posts")
        save_posts(normalized)
        print("Saved posts to social.db")

        posts = normalized
    else:
<<<<<<< HEAD
        _notify("Loading Data", 35, f"Loading existing posts for topic '{topic_query}' from database...")
        from database.db import get_posts
=======
>>>>>>> a400d83d929902c5ff89b65d6dae3c134da879a5
        posts = get_posts(topic_query=topic_query)
        print(f"Loaded {len(posts)} existing posts from DB")

    if not do_analyze:
        _notify("Completed", 100, "Collection completed. Analysis skipped.")
        print("Analysis skipped. Done.")
        return posts

    sentiments = []
    emotions = []
    demographics = []
    trends = []
    network = None

    if posts:
        _notify("Parallel Analytics", 60, f"Running parallel Sentiment, Emotion, Demographic & Trend analysis on {len(posts)} posts...")
        print(f"\n[Parallel Analytics] Processing {len(posts)} posts across models...")
        from concurrent.futures import ThreadPoolExecutor
        from analytics.sentiment import analyze_posts
        from analytics.trends import detect_trends, rising_terms
        from analytics.emotions import analyze_emotions
        from analytics.demographics import analyze_demographics

        with ThreadPoolExecutor(max_workers=4) as executor:
            fut_sent = executor.submit(analyze_posts, posts)
            fut_trend = executor.submit(detect_trends, posts, topic_query, window_size_hours=window_size_hours)
            fut_emot = executor.submit(analyze_emotions, posts) if not skip_emotions else None
            fut_demo = executor.submit(analyze_demographics, posts) if not skip_demographics else None

            sentiments = fut_sent.result() if fut_sent else []
            trends = fut_trend.result() if fut_trend else []
            emotions = fut_emot.result() if fut_emot else []
            demographics = fut_demo.result() if fut_demo else []

        if sentiments:
            save_sentiments(sentiments)
            print(f"  Analyzed sentiment for {len(sentiments)} posts")

        if trends:
            save_trends(trends)
            print(f"  Saved {len(trends)} trend observations")

        hot = rising_terms(posts, window_size_hours=window_size_hours)
        print("\nCurrently rising terms:")
        for kw, freq in hot[:10]:
            print(f"   {kw}: {freq}")

        if emotions:
            save_emotions(emotions)
            print(f"  Analyzed emotions for {len(emotions)} posts")

        if demographics:
            save_demographics(demographics)
            print(f"  Profiled demographics for {len(demographics)} posts")

<<<<<<< HEAD
    if not skip_network and posts:
        _notify("Network Graphing", 88, "Building interaction graph and identifying KOLs...")
        print("\nBuilding network graph...")
=======
    # Always load the full topic corpus for topic-global analyses (network & narrative)
    corpus_posts = get_posts(topic_query=topic_query) or posts
    corpus_sentiments = get_sentiments(topic_query=topic_query) or sentiments
    corpus_emotions = get_emotions(topic_query=topic_query) or emotions
    corpus_demographics = get_demographics(topic_query=topic_query) or demographics
    corpus_network = {
        "nodes": get_network_nodes(topic_query=topic_query),
        "edges": get_network_edges(topic_query=topic_query),
    }
    corpus_trends = get_trends(topic_query=topic_query) or trends

    if not skip_network and (corpus_posts or posts):
        target_posts = corpus_posts or posts
        target_sentiments = corpus_sentiments or sentiments
        print(f"\nBuilding network graph across full corpus ({len(target_posts)} posts)...")
>>>>>>> a400d83d929902c5ff89b65d6dae3c134da879a5
        from analytics.network import analyze_network
        network = analyze_network(target_posts, topic_query, target_sentiments)
        if network["nodes"]:
            save_network_nodes(network["nodes"])
            save_network_edges(network["edges"])
            print(f"  Mapped {len(network['nodes'])} nodes, {len(network['edges'])} edges")
            print(f"  Identified {len(network['kols'])} key opinion leaders")

<<<<<<< HEAD
    if not skip_narrative and posts:
        _notify("Narrative Generation", 94, "Synthesizing executive AI narrative report...")
        print("\nGenerating narrative report...")
=======
    if network is None and (corpus_network["nodes"] or corpus_network["edges"]):
        network = corpus_network

    if not skip_narrative and (corpus_posts or posts):
        target_posts = corpus_posts or posts
        print(f"\nGenerating narrative report across full corpus ({len(target_posts)} posts)...")
>>>>>>> a400d83d929902c5ff89b65d6dae3c134da879a5
        from analytics.narrative import generate_narrative, write_report_file
        narrative = generate_narrative(
            target_posts,
            sentiments=corpus_sentiments or sentiments,
            emotions=corpus_emotions or emotions,
            demographics=corpus_demographics or demographics,
            trends=corpus_trends or trends,
            network=network,
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

    _notify("Completed", 100, f"Successfully processed pipeline for '{topic_query}'.")
    print("\nPipeline complete.")
    return posts


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="AI Social Media Analytics Pipeline")
    parser.add_argument("--topic", default="AI Agents", help="Topic query to search")
    parser.add_argument("--channels", nargs="*", default=["@aipost", "@KDnuggets", "@theaiexecutive"],
                        help="Telegram channels to collect")
    parser.add_argument("--x-queries", nargs="*", default=["AI Agents"],
                        help="X profile discovery queries (1 credit each)")
    parser.add_argument("--x-max-profiles", type=int, default=3,
                        help="X profiles to pull tweets from per discovery query")
    parser.add_argument("--x-max-pages", type=int, default=1,
                        help="Timeline pages per X profile (1 credit each)")
    parser.add_argument("--x-budget-credits", type=int, default=4,
                        help="Per-run cap on Social Fetch credits for X")
    parser.add_argument("--x-tweets-per-page", type=int, default=100,
                        help="Max tweets per X timeline page (API max 100)")
    parser.add_argument("--x-no-include-replies", action="store_true",
                        help="Skip reply tweets in X collection (they are included by default)")
    parser.add_argument("--x-refresh", action="store_true",
                        help="Re-collect X handles already pulled for this topic")
    parser.add_argument("--x-dry-run", action="store_true",
                        help="Print the X collection plan and credit cost, spend nothing")
    parser.add_argument("--x-require-topic", dest="x_require_topic",
                        action="store_true", default=True,
                        help="Require a topic term in the profile name/bio (default on)")
    parser.add_argument("--x-no-require-topic", dest="x_require_topic",
                        action="store_false",
                        help="Allow profiles whose name/bio omit the topic terms")
    parser.add_argument("--x-allow-promo", action="store_true",
                        help="Keep giveaway/token accounts the filter would reject")
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
        youtube_limit=args.yt_limit,
        x_max_profiles=args.x_max_profiles,
        x_max_pages=args.x_max_pages,
        x_budget_credits=args.x_budget_credits,
        x_tweets_per_page=args.x_tweets_per_page,
        x_include_replies=not args.x_no_include_replies,
        x_refresh=args.x_refresh,
        x_dry_run=args.x_dry_run,
        x_require_topic=args.x_require_topic,
        x_allow_promo=args.x_allow_promo,
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
