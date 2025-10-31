# pages/2_🗣️_Session_Feedback.py
# Comprehensive session feedback analytics for Keminggris.

import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime
import re
from io import StringIO

# -----------------------------
# Page Config
# -----------------------------
st.set_page_config(page_title="Keminggris | Session Feedback", page_icon="🗣️", layout="wide")

# -----------------------------
# Helpers
# -----------------------------


# -----------------------------
# Data Loader
# -----------------------------
@st.cache_data(show_spinner=False)
def load_feedback(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df

# -----------------------------
# Data Source
# -----------------------------
DATA_PATH = "feedback.csv"
fb = load_feedback(DATA_PATH)

# -----------------------------
# Sidebar: Filters
# -----------------------------
st.sidebar.header("Filters")

# Session selector
ses = (fb.dropna(subset=['session'])
         .assign(_d=pd.to_datetime(fb['session'], format="%A, %d %B %Y", errors='coerce'))
         .sort_values('_d', ascending=False)
         .drop_duplicates('session'))

session_options = ["All"] + ses['session'].tolist()
session_day_sel = st.sidebar.radio("Session Day", options=["All", "Friday", "Regular"], index=0)

session_sel = st.sidebar.multiselect("Date", options=session_options, default=["All"])
# Apply filters
if (not session_sel) or ("All" in session_sel):
    mask = pd.Series(True, index=fb.index)
else:
    mask = fb["session"].isin(session_sel)

if session_day_sel != "All":
    mask = mask & (fb["session_day"] == session_day_sel)

view = fb.loc[mask].copy()


# -----------------------------
# Header & KPIs
# -----------------------------
LOGO_PATH = "assets/KEMINGGRIS LOGO HD Horizontal.png"
try:
    st.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass
st.title("🗣️ Session Feedback | Keminggris Dashboard")
st.caption("Deep-dive into ratings, interest to return, suggestions, shoutouts, and moderator performance.")

k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Responses", f"{view.shape[0]:,}")
with k2:
    st.metric("Avg Overall", f"{view['overall'].mean():.2f}" if view['overall'].notna().any() else "-")
with k3:
    st.metric("Avg Confidence", f"{view['confidence'].mean():.2f}" if view['confidence'].notna().any() else "-")
with k4:
    st.metric("Avg Comfortable", f"{view['comfortable'].mean():.2f}" if view['comfortable'].notna().any() else "-")
with k5:
    share_yes = (view["interested_next_norm"] == "Yes").mean() if not view.empty else np.nan
    st.metric("Interested again (Yes%)", f"{share_yes*100:,.1f}%" if pd.notna(share_yes) else "-")

st.divider()

# -----------------------------
# Tabs
# -----------------------------
t_overview, t_ratings, t_suggestions, t_moderators, = st.tabs(
    [
        "Overview",
        "Ratings Breakdown",
        "Suggestions",
        "Moderator Insights",
    ]
)

# --- Overview ---
with t_overview:
    st.subheader("Metrics Distributions")
    
    # with c1:
        # 3 histograms for overall / confidence / comfortable
    colA, colB, colC = st.columns(3)

    def score_hist(metric_key: str, title: str):
        if view[metric_key].notna().any():
            d = view[metric_key].round(1).value_counts().reset_index()
            d.columns = ["score", "count"]; d = d.sort_values("score")
            base = (
                alt.Chart(d)
                .transform_joinaggregate(total='sum(count)')
                .transform_calculate(
                    pct='datum.count / datum.total',
                    label="datum.count + ' (' + format(datum.pct, '.0%') + ')'"
                )
            )
            chart = alt.layer(
                base.mark_bar().encode(
                    x=alt.X("score:O", title=f"{title} (1–5)"),
                    y=alt.Y("count:Q", title="Responses"),
                    tooltip=[
                        alt.Tooltip("score:O", title="Score"),
                        alt.Tooltip("count:Q", title="Responses"),
                        alt.Tooltip("pct:Q", title="Percent", format=".0%")
                    ]
                ),
                base.mark_text(align="center", baseline="bottom", dy=-2).encode(
                    x="score:O",
                    y="count:Q",
                    text="label:N"
                )
            ).properties(height=240)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.info(f"No {title.lower()} data in range.")

    with colA: score_hist("overall", "Overall")
    with colB: score_hist("confidence", "Confidence")
    with colC: score_hist("comfortable", "Comfortable")

    c1, cSep, c2 = st.columns([2, 0.06, 1])
    with cSep:
        st.markdown(
            '<div style="border-left:1px solid #ddd;height:100%;margin-left:6px;"></div>',
            unsafe_allow_html=True
        )
    with c1:
        st.subheader("Do participants want to join the next session?")
        share = view.groupby("interested_next_norm").size().reset_index(name="count")
        base = (
            alt.Chart(share)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
            .transform_calculate(
                legend_label="datum.interested_next_norm + ' — ' + format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart = base.mark_arc(innerRadius=60).encode(
            theta="count:Q",
            color=alt.Color("legend_label:N", legend=alt.Legend(title="")),
            tooltip=[
                alt.Tooltip("interested_next_norm:N", title="Interested?"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("pct:Q", title="Percent", format=".0%")
            ]
        ).properties(height=260)
        st.altair_chart(chart, use_container_width=True)

# --- Ratings Breakdown ---
with t_ratings:
    st.subheader("Ratings Breakdown Over Time")
    if view["date"].notna().any():
        melted = (
            view.melt(id_vars=["date", "session", "session_day"], value_vars=["overall","confidence","comfortable"],
                      var_name="metric", value_name="score").dropna()
        )
        base = alt.Chart(melted)
        chart = alt.layer(
            base.mark_line(point=True).encode(
                x=alt.X(
                    "session:N",
                    title="Session",
                    sort=alt.EncodingSortField(field="date", op="min", order="ascending")
                ),
                y=alt.Y("mean(score):Q", title="Average score", scale=alt.Scale(domain=[4, 5])),
                color=alt.Color("metric:N", legend=alt.Legend(title="Metric")),
                tooltip=[
                    "session",
                    "date",
                    "session_day",
                    "metric",
                    alt.Tooltip("count():Q", title="Responses"),
                    alt.Tooltip("mean(score):Q", title="Average", format=".2f")
                ]
            ),
            base.mark_text(align="center", baseline="bottom", dy=-8).encode(
                x=alt.X(
                    "session:N",
                    sort=alt.EncodingSortField(field="date", op="min", order="ascending")
                ),
                y=alt.Y("mean(score):Q", scale=alt.Scale(domain=[4, 5])),
                color="metric:N",
                text=alt.Text("mean(score):Q", format=".2f")
            )
        ).properties(height=360)
        st.altair_chart(chart)
    else:
        st.info("No dated records available to plot time trends.")


# --- Suggestions ---
with t_suggestions:
    st.title("🧩 Suggestions | Sentiment & Themes")
    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total suggestions", f"{view['suggestions'].notna().sum():,}")
    with k2: st.metric("Positive %", f"{(view['sentiment'].eq('Positive').mean()*100):.1f}%")
    with k3: st.metric("Negative %", f"{(view['sentiment'].eq('Negative').mean()*100):.1f}%")
    with k4: st.metric("Neutral %", f"{(view['sentiment'].eq('Neutral').mean()*100):.1f}%")

    # ---------- Charts ----------
    colA, sep, colB = st.columns([2, 0.06, 2])
    with colA:
        st.subheader("Sentiment distribution")
        sent_counts = view["sentiment"].value_counts().rename_axis("sentiment").reset_index(name="count")
        sorted_sent = sent_counts.sort_values("count", ascending=False)["sentiment"].tolist()
        base = (
            alt.Chart(sent_counts)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart = alt.layer(
            base.mark_bar().encode(
                x=alt.X("count:Q", title="Count"),
                y=alt.Y("sentiment:N", sort=sorted_sent),
                tooltip=[
                    alt.Tooltip("sentiment:N", title="Sentiment"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("pct:Q", title="Percent", format=".0%")
                ]
            ),
            base.mark_text(align="left", baseline="middle", dx=3).encode(
                x="count:Q",
                y=alt.Y("sentiment:N", sort=sorted_sent),
                text="label:N"
            )
        ).properties(height=240)
        st.altair_chart(chart, use_container_width=True)

    with colB:
        st.subheader("Top themes")
        theme_counts = {}
        view_themes = view["themes"].dropna().tolist()
        for s in view_themes:
            for t in [x.strip() for x in str(s).split(";") if x.strip()]:
                theme_counts[t] = theme_counts.get(t, 0) + 1
        theme_df = pd.DataFrame(sorted(theme_counts.items(), key=lambda x: -x[1]), columns=["theme","count"])
        if not theme_df.empty:
            top = theme_df.head(15)
            sorted_themes = top.sort_values("count", ascending=False)["theme"].tolist()
            base = (
                alt.Chart(top)
                .transform_joinaggregate(total='sum(count)')
                .transform_calculate(
                    pct='datum.count / datum.total',
                    label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
                )
            )
            chart = alt.layer(
                base.mark_bar().encode(
                    x=alt.X("count:Q", title="Count"),
                    y=alt.Y("theme:N", sort=sorted_themes),
                    tooltip=[
                        alt.Tooltip("theme:N", title="Theme"),
                        alt.Tooltip("count:Q", title="Count"),
                        alt.Tooltip("pct:Q", title="Percent", format=".0%")
                    ]
                ),
                base.mark_text(align="left", baseline="middle", dx=3).encode(
                    x="count:Q",
                    y=alt.Y("theme:N", sort=sorted_themes),
                    text="label:N"
                )
            ).properties(height=350)
            st.altair_chart(chart, use_container_width=False)
        else:
            st.info("No themes detected in the current filter.")

    # Filters and table of suggestions
    all_themes = sorted({
        t.strip()
        for s in view["themes"].dropna()
        for t in str(s).split(";")
        if t.strip()
    })
    theme_filter_opts = ["All"] + all_themes
    sentiment_present = [s for s in ["Positive","Neutral","Negative", "Constructive"] if (view["sentiment"] == s).any()]
    sentiment_filter_opts = ["All"] + sentiment_present

    f1, f2 = st.columns(2)
    with f1:
        sel_theme = st.selectbox("Filter by theme", options=theme_filter_opts, index=0)
    with f2:
        sel_sentiment = st.selectbox("Filter by sentiment", options=sentiment_filter_opts, index=0)

    filtered = view.copy()
    if sel_theme != "All":
        pattern = rf"(?:^|;\s*){re.escape(sel_theme)}(?:\s*;|$)"
        filtered = filtered[filtered["themes"].fillna("").str.contains(pattern, regex=True)]
    if sel_sentiment != "All":
        filtered = filtered[filtered["sentiment"] == sel_sentiment]

    st.subheader("Suggestions table")
    st.dataframe(
        filtered[["session","sentiment","themes","suggestions"]]
            .sort_values("session", ascending=False),
        use_container_width=True,
        height=420
    )


# --- Moderator Insights ---
with t_moderators:
    st.title("🧩 Moderator Suggestions | Sentiment")

    k1, k2, k3, k4 = st.columns(4)
    with k1: st.metric("Total suggestions", f"{view['suggestions'].notna().sum():,}")
    with k2: st.metric("Positive %", f"{(view['moderator_sentiment'].eq('Positive').mean()*100):.1f}%")
    with k3: st.metric("Negative %", f"{(view['moderator_sentiment'].eq('Negative').mean()*100):.1f}%")
    with k4: st.metric("Neutral %", f"{(view['moderator_sentiment'].eq('Neutral').mean()*100):.1f}%")

    # ---------- Charts ----------
    colA, sep, colB = st.columns([2, 0.06, 2])
    with colA:
        st.subheader("Moderator Sentiment distribution")
        sent_counts = view["moderator_sentiment"].value_counts().rename_axis("moderator_sentiment").reset_index(name="count")
        sorted_ms = sent_counts.sort_values("count", ascending=False)["moderator_sentiment"].tolist()
        base = (
            alt.Chart(sent_counts)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart = alt.layer(
            base.mark_bar().encode(
                x=alt.X("count:Q", title="Count"),
                y=alt.Y("moderator_sentiment:N", sort=sorted_ms),
                tooltip=[
                    alt.Tooltip("moderator_sentiment:N", title="Sentiment"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("pct:Q", title="Percent", format=".0%")
                ]
            ),
            base.mark_text(align="left", baseline="middle", dx=3).encode(
                x="count:Q",
                y=alt.Y("moderator_sentiment:N", sort=sorted_ms),
                text="label:N"
            )
        ).properties(height=350)
        st.altair_chart(chart, use_container_width=False)

    with colB:
        st.subheader("Moderator Name Mention Count")
        mod_counts = view["moderator_name"].value_counts().rename_axis("moderator_name").reset_index(name="count")
        sorted_mods = mod_counts.sort_values("count", ascending=False)["moderator_name"].tolist()
        base2 = (
            alt.Chart(mod_counts)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart2 = alt.layer(
            base2.mark_bar().encode(
                x=alt.X("count:Q", title="Count"),
                y=alt.Y("moderator_name:N", sort=sorted_mods),
                tooltip=[
                    alt.Tooltip("moderator_name:N", title="Moderator"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("pct:Q", title="Percent", format=".0%")
                ]
            ),
            base2.mark_text(align="left", baseline="middle", dx=3).encode(
                x="count:Q",
                y=alt.Y("moderator_name:N", sort=sorted_mods),
                text="label:N"
            )
        ).properties(height=350)
        st.altair_chart(chart2, use_container_width=False)

    moderator_name_present = view["moderator_name"].dropna().unique().tolist()
    moderator_name_filter_opts = ["All"] + moderator_name_present
    sentiment_present = [s for s in ["Positive","Neutral","Negative", "Constructive"] if (view["moderator_sentiment"] == s).any()]
    sentiment_filter_opts = ["All"] + sentiment_present

    f1, f2 = st.columns(2)
    with f1:
        sel_moderator_name = st.selectbox("Filter by moderator name", options=moderator_name_filter_opts, index=0)
    with f2:
        sel_sentiment = st.selectbox("Filter by sentiment", options=sentiment_filter_opts, index=0)

    filtered = view.copy()
    if sel_moderator_name != "All":
        pattern = rf"(?:^|;\s*){re.escape(sel_moderator_name)}(?:\s*;|$)"
        filtered = filtered[filtered["moderator_name"].fillna("").str.contains(pattern, regex=True)]
    if sel_sentiment != "All":
        filtered = filtered[filtered["moderator_sentiment"] == sel_sentiment]

    st.subheader("Suggestions table")
    st.dataframe(
        filtered[["session","moderator_name","moderator_sentiment","moderator_suggestions"]]
            .sort_values("session", ascending=False),
        use_container_width=True,
        height=420
    )
    

# --- Export / Raw ---
