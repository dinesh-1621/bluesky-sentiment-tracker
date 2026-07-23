"""
app.py
Auto-refreshing Streamlit dashboard for the Bluesky Sentiment Tracker.
Reads from sentiment_data.db (written to by data_pipeline.py).

Run in a separate terminal from the pipeline:
    streamlit run app.py
"""

import sqlite3
import time

import pandas as pd
import plotly.express as px
import streamlit as st

DB_PATH = "sentiment_data.db"
REFRESH_SECONDS = 7

st.set_page_config(page_title="Bluesky Sentiment Tracker", layout="wide")


def load_data() -> pd.DataFrame:
    try:
        conn = sqlite3.connect(DB_PATH)
        # Pull latest 1000 posts so each individual keyword has plenty of data
        df = pd.read_sql_query(
            "SELECT * FROM comments ORDER BY timestamp DESC LIMIT 1000", conn
        )
        conn.close()
    except sqlite3.Error:
        return pd.DataFrame()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def render_dashboard():
    df_all = load_data()

    st.title("🔴🟡🟢 Real-Time Bluesky Sentiment Tracker")

    if df_all.empty:
        st.warning("No data yet. Make sure `data_pipeline.py` is running in another terminal.")
        return

    # --- Sidebar Keyword Filter ---
    st.sidebar.header("🔍 Topic Filter")
    
    # Get all unique keywords present in the database
    available_keywords = sorted(df_all["keyword_matched"].dropna().unique().tolist())
    
    selected_keyword = st.sidebar.selectbox(
        "Select Keyword / Topic to View:",
        options=["All (Combined)"] + available_keywords,
        index=0
    )

    # Filter dataframe based on selection
    if selected_keyword != "All (Combined)":
        df = df_all[df_all["keyword_matched"] == selected_keyword]
    else:
        df = df_all

    st.caption(
        f"Last updated: {pd.Timestamp.now().strftime('%H:%M:%S')} — "
        f"Refreshes every {REFRESH_SECONDS}s | "
        f"Viewing Topic: **{selected_keyword}** ({len(df)} posts)"
    )

    if df.empty:
        st.info(f"No posts captured yet for keyword '{selected_keyword}'.")
        return

    # --- Top metrics row ---
    col1, col2, col3, col4 = st.columns(4)
    avg_sentiment = df["sentiment_score"].mean()
    col1.metric("Average Sentiment", f"{avg_sentiment:.3f}")
    col2.metric("Total Posts Captured", len(df))
    pct_positive = (df["sentiment_label"] == "Positive").mean() * 100
    pct_negative = (df["sentiment_label"] == "Negative").mean() * 100
    col3.metric("% Positive", f"{pct_positive:.1f}%")
    col4.metric("% Negative", f"{pct_negative:.1f}%")

    st.divider()

    # --- Trend chart & Pie distribution ---
    left, right = st.columns([2, 1])

    with left:
        df_sorted = df.sort_values("timestamp")
        fig_line = px.line(
            df_sorted,
            x="timestamp",
            y="sentiment_score",
            title=f"Sentiment Score Over Time — [{selected_keyword}]",
            markers=True,
        )
        fig_line.add_hline(y=0, line_dash="dash", line_color="gray")
        st.plotly_chart(fig_line, use_container_width=True)

    with right:
        fig_dist = px.pie(
            df,
            names="sentiment_label",
            title=f"Sentiment Distribution — [{selected_keyword}]",
            color="sentiment_label",
            color_discrete_map={
                "Positive": "#2ecc71",
                "Negative": "#e74c3c",
                "Neutral": "#95a5a6",
            },
        )
        st.plotly_chart(fig_dist, use_container_width=True)

    st.divider()

    # --- Live scrolling post feed ---
    st.subheader(f"Latest Posts ({selected_keyword})")

    icon_map = {"Positive": "🟢", "Negative": "🔴", "Neutral": "🟡"}

    for _, row in df.head(25).iterrows():
        icon = icon_map.get(row["sentiment_label"], "⚪")
        short_author = str(row["author"])[:20] + "…"
        st.markdown(
            f"{icon} **{short_author}** · matched *'{row['keyword_matched']}'* "
            f"· score `{row['sentiment_score']:.2f}` · "
            f"{row['timestamp'].strftime('%H:%M:%S')}\n\n"
            f"> {row['text'][:280]}"
        )
        st.markdown("---")


render_dashboard()

# --- Auto-refresh logic ---
time.sleep(REFRESH_SECONDS)
st.rerun()