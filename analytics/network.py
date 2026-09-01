import json
import re
from datetime import datetime, timezone

import networkx as nx


def _extract_mentions(text):
    return re.findall(r"@(\w+)", text)


def build_graph(posts, sentiments=None):
    G = nx.DiGraph()

    sentiment_map = {}
    if sentiments:
        for s in sentiments:
            sentiment_map[s["post_id"]] = s.get("label", "neutral")

    author_posts = {}
    for p in posts:
        handle = p.get("author_handle")
        if not handle:
            continue
        if handle not in author_posts:
            author_posts[handle] = []
        author_posts[handle].append(p)

    for handle in author_posts:
        G.add_node(handle, post_count=len(author_posts[handle]))

    for p in posts:
        handle = p.get("author_handle")
        if not handle:
            continue

        parent_id = p.get("parent_id")
        if parent_id:
            for other_handle, other_posts in author_posts.items():
                if other_handle == handle:
                    continue
                for op in other_posts:
                    if op["id"] == parent_id:
                        if G.has_edge(other_handle, handle):
                            G[other_handle][handle]["weight"] += 1
                        else:
                            G.add_edge(other_handle, handle, weight=1)
                        break

        mentions = _extract_mentions(p.get("text", ""))
        for mentioned in mentions:
            if mentioned != handle and mentioned in author_posts:
                if G.has_edge(handle, mentioned):
                    G[handle][mentioned]["weight"] += 1
                else:
                    G.add_edge(handle, mentioned, weight=1)

    return G


def compute_centrality(G):
    if len(G) == 0:
        return {}

    degree = nx.degree_centrality(G)

    betweenness = nx.betweenness_centrality(G, weight="weight")

    try:
        eigenvector = nx.eigenvector_centrality(G, max_iter=1000, weight="weight")
    except nx.PowerIterationFailedConvergence:
        eigenvector = {n: 0.0 for n in G.nodes()}

    results = {}
    for node in G.nodes():
        results[node] = {
            "degree_centrality": float(round(degree.get(node, 0.0), 6)),
            "betweenness_centrality": float(round(betweenness.get(node, 0.0), 6)),
            "eigenvector_centrality": float(round(eigenvector.get(node, 0.0), 6)),
        }

    return results


def detect_communities(G):
    if len(G) == 0:
        return {}

    undirected = G.to_undirected()

    try:
        communities_list = nx.community.louvain_communities(
            undirected, weight="weight", seed=42
        )
    except Exception:
        return {n: 0 for n in G.nodes()}

    community_map = {}
    for idx, community in enumerate(communities_list):
        for node in community:
            community_map[node] = idx

    return community_map


def track_sentiment_flow(G, posts, sentiments):
    sentiment_map = {}
    for s in sentiments:
        sentiment_map[s["post_id"]] = s.get("label", "neutral")

    edge_sentiment = {}
    for u, v in G.edges():
        u_posts = [p for p in posts if p.get("author_handle") == u]
        v_posts = [p for p in posts if p.get("author_handle") == v]

        u_sentiments = [sentiment_map.get(p["id"]) for p in u_posts if p["id"] in sentiment_map]
        v_sentiments = [sentiment_map.get(p["id"]) for p in v_posts if p["id"] in sentiment_map]

        if u_sentiments and v_sentiments:
            from_label = max(set(u_sentiments), key=u_sentiments.count)
            to_label = max(set(v_sentiments), key=v_sentiments.count)
            edge_sentiment[(u, v)] = json.dumps({"from": from_label, "to": to_label})
        else:
            edge_sentiment[(u, v)] = json.dumps({"from": "unknown", "to": "unknown"})

    return edge_sentiment


def identify_kols(centrality_map, top_pct=0.1):
    if not centrality_map:
        return set()

    sorted_handles = sorted(
        centrality_map.keys(),
        key=lambda h: centrality_map[h]["eigenvector_centrality"],
        reverse=True,
    )

    n_kols = max(1, int(len(sorted_handles) * top_pct))
    return set(sorted_handles[:n_kols])


def analyze_network(posts, topic_query, sentiments=None):
    if not posts:
        return {"nodes": [], "edges": [], "kols": []}

    G = build_graph(posts, sentiments)

    if len(G) == 0:
        return {"nodes": [], "edges": [], "kols": []}

    centrality = compute_centrality(G)
    communities = detect_communities(G)
    sentiment_flow = track_sentiment_flow(G, posts, sentiments or [])
    kols = identify_kols(centrality)

    computed_at = datetime.now(timezone.utc).isoformat()

    nodes = []
    for handle in G.nodes():
        c = centrality.get(handle, {})
        nodes.append({
            "handle": handle,
            "topic_query": topic_query,
            "degree_centrality": c.get("degree_centrality", 0.0),
            "betweenness_centrality": c.get("betweenness_centrality", 0.0),
            "eigenvector_centrality": c.get("eigenvector_centrality", 0.0),
            "community_id": communities.get(handle, 0),
            "is_kol": 1 if handle in kols else 0,
            "computed_at": computed_at,
        })

    edges = []
    for u, v, data in G.edges(data=True):
        edges.append({
            "source_handle": u,
            "target_handle": v,
            "weight": data.get("weight", 1),
            "sentiment_shift": sentiment_flow.get((u, v), json.dumps({"from": "unknown", "to": "unknown"})),
            "topic_query": topic_query,
            "computed_at": computed_at,
        })

    return {"nodes": nodes, "edges": edges, "kols": list(kols)}
