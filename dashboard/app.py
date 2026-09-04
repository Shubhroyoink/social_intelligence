import os
import sys
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from database.db import (
    create_database, get_posts, get_sentiments, get_trends, get_emotions,
    get_demographics_summary, get_network_nodes, get_network_edges,
    get_narratives,
)

st.set_page_config(page_title="AI Social Media Analytics", layout="wide")


@st.cache_data(ttl=60)
def load_data(topic):
    t = topic if topic != "All" else None
    return {
        "posts": get_posts(topic_query=t),
        "sentiments": get_sentiments(topic_query=t),
        "trends": get_trends(topic_query=t),
        "emotions": get_emotions(topic_query=t),
        "demo_summary": get_demographics_summary(topic_query=t),
        "network_nodes": get_network_nodes(topic_query=t),
        "network_edges": get_network_edges(topic_query=t),
        "narratives": get_narratives(topic_query=t),
    }


EMOTION_COLORS = {
    "anger": "#e74c3c",
    "disgust": "#8e44ad",
    "fear": "#e67e22",
    "joy": "#2ecc71",
    "neutral": "#95a5a6",
    "sadness": "#3498db",
    "surprise": "#f1c40f",
}


def main():
    st.title("AI Social Media Analytics")

    create_database()  # idempotent; ensures schema exists even if pipeline hasn't run

    st.sidebar.header("Filters")
    all_posts = get_posts()
    topics = ["All"] + sorted({p["topic_query"] for p in all_posts if p.get("topic_query")})
    topic = st.sidebar.selectbox("Topic", topics)

    data = load_data(topic)
    posts = data["posts"]
    sentiments = data["sentiments"]
    trends = data["trends"]
    emotions = data["emotions"]
    demo_summary = data["demo_summary"]
    net_nodes = data["network_nodes"]
    net_edges = data["network_edges"]

    narratives = data["narratives"]
    if narratives:
        latest = narratives[0]
        st.subheader("Executive Summary / AI Narrative")
        caption = f"Generated {latest['created_at'][:19].replace('T', ' ')} UTC"
        if latest["backend"] == "gemini":
            caption += f" \u00b7 Gemini ({latest['model']})"
        else:
            caption += " \u00b7 template fallback (no LLM_API_KEY set)"
        st.caption(caption)
        st.markdown(latest["report_markdown"])
        st.markdown("---")

    df_posts = pd.DataFrame(posts)
    df_sent = pd.DataFrame(sentiments)

    if df_sent.empty:
        st.info("No analyzed data yet. Run the pipeline first: python run_pipeline.py")
        return

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Posts Collected", len(df_posts))
    c2.metric("Posts Analyzed", len(df_sent))
    c3.metric("Positive", f"{(df_sent['label'] == 'positive').mean() * 100:.1f}%")
    c4.metric("Negative", f"{(df_sent['label'] == 'negative').mean() * 100:.1f}%")

    st.markdown("---")

    st.subheader("Sentiment Distribution")
    dist = df_sent["label"].value_counts().rename_axis("label").reset_index(name="count")
    colors = {"positive": "#2ca02c", "neutral": "#999999", "negative": "#d62728"}
    fig = px.pie(dist, names="label", values="count", color="label",
                 color_discrete_map=colors, hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Sentiment Timeline")
    df_sent_time = df_sent.copy()
    df_sent_time["created_at"] = pd.to_datetime(df_sent_time["created_at"], errors="coerce")
    df_sent_time = df_sent_time.dropna(subset=["created_at"]).sort_values("created_at")

    daily = df_sent_time.set_index("created_at").resample("1D").apply(
        lambda x: pd.Series({
            "positive": (x["label"] == "positive").mean() * 100,
            "neutral": (x["label"] == "neutral").mean() * 100,
            "negative": (x["label"] == "negative").mean() * 100,
            "count": len(x),
        })
    ).reset_index()

    fig2 = px.line(daily, x="created_at", y=["positive", "neutral", "negative"],
                   labels={"value": "Percentage", "created_at": "Date",
                           "variable": "Sentiment"})
    st.plotly_chart(fig2, use_container_width=True)

    if "platform" in df_sent.columns:
        st.subheader("Sentiment by Platform")
        cross = pd.crosstab(df_sent["platform"], df_sent["label"], normalize="index") * 100
        fig3 = px.bar(cross.reset_index().melt(id_vars="platform"),
                      x="platform", y="value", color="label",
                      labels={"value": "Percentage", "platform": "Platform"})
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    df_trends = pd.DataFrame(trends)
    if not df_trends.empty:
        st.subheader("Trending Terms")
        df_trends["window_start"] = pd.to_datetime(df_trends["window_start"], errors="coerce")
        latest = df_trends["window_start"].max()
        latest_trends = df_trends[df_trends["window_start"] == latest] \
            .sort_values("frequency", ascending=False).head(20)

        c5, c6 = st.columns(2)
        with c5:
            st.markdown("**Top terms (latest window)**")
            top_hot = latest_trends.reset_index().head(10)
            for idx, row in top_hot.iterrows():
                st.write(f"**{row['keyword']}** ({row['frequency']} mentions)")

        with c6:
            st.markdown("**Trend over time**")
            keyword_sel = st.selectbox("Select keyword", latest_trends["keyword"].unique()[:10])
            kw_time = df_trends[df_trends["keyword"] == keyword_sel] \
                .groupby("window_start")["frequency"].sum().reset_index()
            if not kw_time.empty:
                fig4 = px.line(kw_time, x="window_start", y="frequency", title=keyword_sel)
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    df_emotions = pd.DataFrame(emotions)
    if not df_emotions.empty:
        st.subheader("Emotion Analysis")

        col_a, col_b = st.columns([1, 3])
        with col_a:
            sarcasm_pct = df_emotions["sarcasm_flag"].mean() * 100
            st.metric("Sarcasm Detected", f"{sarcasm_pct:.1f}%")
            stance_dist = df_emotions["stance"].value_counts()
            st.markdown("**Stance Breakdown**")
            for stance_label, count in stance_dist.items():
                pct = count / len(df_emotions) * 100
                st.write(f"  {stance_label}: {count} ({pct:.1f}%)")

        with col_b:
            emotion_counts = df_emotions["primary_emotion"].value_counts().reset_index()
            emotion_counts.columns = ["emotion", "count"]
            fig_emo = px.bar(
                emotion_counts, x="count", y="emotion", orientation="h",
                color="emotion", color_discrete_map=EMOTION_COLORS,
                labels={"count": "Posts", "emotion": "Emotion"},
            )
            fig_emo.update_layout(showlegend=False, yaxis={"categoryorder": "total ascending"})
            st.plotly_chart(fig_emo, use_container_width=True)

        st.subheader("Emotion Timeline")
        df_emo_time = df_emotions.copy()
        df_emo_time["created_at"] = pd.to_datetime(df_emo_time.get("created_at"), errors="coerce")
        df_emo_time = df_emo_time.dropna(subset=["created_at"]).sort_values("created_at")

        if not df_emo_time.empty:
            emo_daily = df_emo_time.set_index("created_at").resample("1D").apply(
                lambda x: pd.Series({
                    emo: (x["primary_emotion"] == emo).mean() * 100
                    for emo in EMOTION_COLORS
                })
            ).reset_index()

            fig_emo_time = px.line(
                emo_daily, x="created_at",
                y=list(EMOTION_COLORS.keys()),
                labels={"value": "Percentage", "created_at": "Date", "variable": "Emotion"},
                color_discrete_map=EMOTION_COLORS,
            )
            st.plotly_chart(fig_emo_time, use_container_width=True)

        st.subheader("Stance Analysis")
        stance_dist = df_emotions["stance"].value_counts().reset_index()
        stance_dist.columns = ["stance", "count"]
        stance_colors = {"supportive": "#2ca02c", "against": "#d62728", "neutral": "#999999"}
        fig_stance = px.pie(
            stance_dist, names="stance", values="count", color="stance",
            color_discrete_map=stance_colors, hole=0.4,
        )
        st.plotly_chart(fig_stance, use_container_width=True)

    st.markdown("---")

    if demo_summary and any(demo_summary.values()):
        st.subheader("Demographics")

        demo_cols = st.columns(3)

        with demo_cols[0]:
            st.markdown("**Language Distribution**")
            langs = demo_summary.get("languages", {})
            if langs:
                lang_df = pd.DataFrame(list(langs.items()), columns=["language", "count"])
                fig_lang = px.pie(lang_df, names="language", values="count", hole=0.4)
                st.plotly_chart(fig_lang, use_container_width=True)
            else:
                st.info("No language data")

        with demo_cols[1]:
            st.markdown("**Geographic Mentions**")
            geo = demo_summary.get("geo", {})
            if geo:
                geo_df = pd.DataFrame(list(geo.items()), columns=["region", "count"])
                geo_df = geo_df.sort_values("count", ascending=True).head(15)
                fig_geo = px.bar(geo_df, x="count", y="region", orientation="h",
                                 labels={"count": "Mentions", "region": "Region"})
                st.plotly_chart(fig_geo, use_container_width=True)
            else:
                st.info("No geographic data")

        with demo_cols[2]:
            st.markdown("**Professional Interests**")
            interests = demo_summary.get("interests", {})
            if interests:
                int_df = pd.DataFrame(list(interests.items()), columns=["interest", "count"])
                int_df = int_df.sort_values("count", ascending=True)
                fig_int = px.bar(int_df, x="count", y="interest", orientation="h",
                                 labels={"count": "Posts", "interest": "Category"})
                st.plotly_chart(fig_int, use_container_width=True)
            else:
                st.info("No interest data")

    st.markdown("---")

    if net_nodes:
        st.subheader("Network & Influence Analysis")

        df_nodes = pd.DataFrame(net_nodes)
        df_edges = pd.DataFrame(net_edges) if net_edges else pd.DataFrame()

        kol_count = df_nodes["is_kol"].sum()
        n1, n2, n3 = st.columns(3)
        n1.metric("Network Nodes", len(df_nodes))
        n2.metric("Connections", len(df_edges))
        n3.metric("Key Opinion Leaders", kol_count)

        st.markdown("**Key Opinion Leaders**")
        kols = df_nodes[df_nodes["is_kol"] == 1].sort_values(
            "eigenvector_centrality", ascending=False
        )
        if not kols.empty:
            kol_display = kols[["handle", "degree_centrality", "betweenness_centrality",
                                "eigenvector_centrality", "community_id"]].copy()
            kol_display.columns = ["Handle", "Degree", "Betweenness", "Eigenvector", "Community"]
            st.dataframe(kol_display, use_container_width=True)
        else:
            st.info("No KOLs identified yet (need more interaction data)")

        if not df_nodes.empty and not df_edges.empty:
            st.markdown("**Network Graph**")
            try:
                import networkx as nx
                import numpy as np

                G = nx.DiGraph()
                for _, row in df_nodes.iterrows():
                    G.add_node(row["handle"],
                               eigenvector=row["eigenvector_centrality"],
                               community=row["community_id"],
                               is_kol=row["is_kol"])

                for _, row in df_edges.iterrows():
                    G.add_edge(row["source_handle"], row["target_handle"],
                               weight=row["weight"])

                if len(G.nodes()) > 0:
                    pos = nx.spring_layout(G, k=2.0 / np.sqrt(max(len(G.nodes()), 1)),
                                           seed=42, iterations=50)

                    node_x = [pos[n][0] for n in G.nodes()]
                    node_y = [pos[n][1] for n in G.nodes()]
                    node_text = list(G.nodes())

                    node_sizes = []
                    node_colors = []
                    for n in G.nodes():
                        data = G.nodes[n]
                        size = 10 + data.get("eigenvector", 0) * 200
                        node_sizes.append(max(size, 8))
                        node_colors.append(data.get("community", 0))

                    edge_x = []
                    edge_y = []
                    for u, v in G.edges():
                        x0, y0 = pos[u]
                        x1, y1 = pos[v]
                        edge_x.extend([x0, x1, None])
                        edge_y.extend([y0, y1, None])

                    fig_net = go.Figure()
                    fig_net.add_trace(go.Scatter(
                        x=edge_x, y=edge_y, mode="lines",
                        line=dict(width=0.5, color="#888"),
                        hoverinfo="none", showlegend=False,
                    ))
                    fig_net.add_trace(go.Scatter(
                        x=node_x, y=node_y, mode="markers+text",
                        text=node_text, textposition="top center",
                        textfont=dict(size=8),
                        marker=dict(
                            size=node_sizes, color=node_colors,
                            colorscale="Viridis", showscale=True,
                            colorbar=dict(title="Community"),
                        ),
                        hoverinfo="text", showlegend=False,
                    ))
                    fig_net.update_layout(
                        showlegend=False, height=600,
                        xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                        margin=dict(b=20, l=20, r=20, t=20),
                    )
                    st.plotly_chart(fig_net, use_container_width=True)
            except Exception as e:
                st.warning(f"Could not render network graph: {e}")

    st.markdown("---")

    st.subheader("Word Cloud")
    try:
        from wordcloud import WordCloud
        import matplotlib.pyplot as plt

        all_text = " ".join(p.get("text", "") for p in posts if p.get("text"))
        if all_text.strip():
            wc = WordCloud(
                width=1200, height=400, background_color="white",
                colormap="viridis", max_words=100,
            ).generate(all_text)
            fig_wc, ax = plt.subplots(figsize=(12, 4))
            ax.imshow(wc, interpolation="bilinear")
            ax.axis("off")
            st.pyplot(fig_wc)
            plt.close(fig_wc)
        else:
            st.info("Not enough text data for word cloud")
    except Exception as e:
        st.warning(f"Word cloud unavailable: {e}")

    st.markdown("---")

    with st.expander("View sample posts"):
        if not df_posts.empty:
            cols = ["platform", "author_handle", "text", "created_at"]
            available = [c for c in cols if c in df_posts.columns]
            st.dataframe(df_posts[available].head(20), use_container_width=True)


if __name__ == "__main__":
    main()
