import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import plotly.express as px
import streamlit as st

from database.db import get_posts, get_sentiments, get_trends

st.set_page_config(page_title="AI Social Media Analytics", layout="wide")


@st.cache_data(ttl=60)
def load_data(topic):
    posts = get_posts(topic_query=topic) if topic != "All" else get_posts()
    sentiments = get_sentiments(topic_query=topic) if topic != "All" else get_sentiments()
    trends = get_trends(topic_query=topic) if topic != "All" else get_trends()
    return posts, sentiments, trends


def main():
    st.title("AI Social Media Analytics")

    # ---- Sidebar ----
    st.sidebar.header("Filters")
    all_posts = get_posts()
    topics = ["All"] + sorted({p["topic_query"] for p in all_posts if p.get("topic_query")})
    topic = st.sidebar.selectbox("Topic", topics)

    posts, sentiments, trends = load_data(topic)

    # ---- Top metrics ----
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

    # ---- Sentiment distribution ----
    st.subheader("Sentiment Distribution")
    dist = df_sent["label"].value_counts().rename_axis("label").reset_index(name="count")
    colors = {"positive": "#2ca02c", "neutral": "#999999", "negative": "#d62728"}
    fig = px.pie(dist, names="label", values="count", color="label",
                 color_discrete_map=colors, hole=0.4)
    st.plotly_chart(fig, use_container_width=True)

    # ---- Sentiment over time ----
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

    # ---- Platform comparison ----
    if "platform" in df_sent.columns:
        st.subheader("Sentiment by Platform")
        cross = pd.crosstab(df_sent["platform"], df_sent["label"], normalize="index") * 100
        fig3 = px.bar(cross.reset_index().melt(id_vars="platform"),
                      x="platform", y="value", color="label",
                      labels={"value": "Percentage", "platform": "Platform"})
        st.plotly_chart(fig3, use_container_width=True)

    st.markdown("---")

    # ---- Trends ----
    st.subheader("Trending Terms")
    df_trends = pd.DataFrame(trends)

    if df_trends.empty:
        st.info("No trend data yet.")
    else:
        # Current rising terms: latest window
        df_trends["window_start"] = pd.to_datetime(df_trends["window_start"], errors="coerce")
        latest = df_trends["window_start"].max()
        latest_trends = df_trends[df_trends["window_start"] == latest] \
            .sort_values("frequency", ascending=False).head(20)

        c5, c6 = st.columns(2)
        with c5:
            st.markdown(f"**Top terms (latest window)**")
            top_hot = latest_trends.reset_index().head(10)
            for idx, row in top_hot.iterrows():
                st.write(f"• **{row['keyword']}**  ({row['frequency']} mentions)")

        with c6:
            st.markdown("**Trend over time**")
            keyword_sel = st.selectbox("Select keyword", latest_trends["keyword"].unique()[:10])
            kw_time = df_trends[df_trends["keyword"] == keyword_sel] \
                .groupby("window_start")["frequency"].sum().reset_index()
            if not kw_time.empty:
                fig4 = px.line(kw_time, x="window_start", y="frequency", title=keyword_sel)
                st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")

    # ---- Sample posts ----
    with st.expander("View sample posts"):
        if not df_posts.empty:
            sample = df_posts[["platform", "author_handle", "text", "created_at"]].head(20)
            st.dataframe(sample, use_container_width=True)


if __name__ == "__main__":
    main()
