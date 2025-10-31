import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
import re

st.set_page_config(page_title="Keminggris | Moderator Feedback", page_icon="🧑‍🏫", layout="wide")

@st.cache_data(show_spinner=False)
def load_momod_feedback(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    return df

DATA_PATH = "momod_feedback.csv"
mf = load_momod_feedback(DATA_PATH)

# Sidebar filters
st.sidebar.header("Filters")

session_types = ["All", "Friday", "Regular"]
session_day_sel = st.sidebar.radio("Session", options=session_types, index=0)

dates_all = [s for s in mf["session_label"].dropna().unique().tolist()]
date_sel = st.sidebar.multiselect("Date", options=["All"] + dates_all, default=["All"])

mods_all = sorted([m for m in mf.get("moderator_name", pd.Series(dtype=str)).dropna().unique().tolist()])
mod_options = ["All"] + mods_all
mods_sel = st.sidebar.selectbox("Moderator", options=mod_options, index=0)

# Build mask
mask = pd.Series(True, index=mf.index)
if session_day_sel != "All":
    mask = mask & (mf["session_day"] == session_day_sel)
if date_sel and ("All" not in date_sel):
    mask = mask & (mf["session_label"].isin(date_sel))
if mods_sel != "All":
    mask = mask & (mf["moderator_name"] == mods_sel)

view = mf.loc[mask].copy()

LOGO_PATH = "assets/KEMINGGRIS LOGO HD Horizontal.png"
try:
    st.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass
st.title("🧑‍🏫 Moderator Feedback | Keminggris Dashboard")
st.caption("Insights from moderators on session quality, flow, engagement, and concerns.")

# KPIs
k1, k2, k3, k4, k5 = st.columns(5)
with k1:
    st.metric("Responses", f"{view.shape[0]:,}")
with k2:
    st.metric("Avg Overall", f"{view['overall'].mean():.2f}" if view['overall'].notna().any() else "-")
with k3:
    st.metric("Avg Time Allocation", f"{view['time_allocation'].mean():.2f}" if view['time_allocation'].notna().any() else "-")
with k4:
    st.metric("Avg Conversation Flow", f"{view['conversation_flow'].mean():.2f}" if view['conversation_flow'].notna().any() else "-")
with k5:
    st.metric("Avg Engagement", f"{view['engagement'].mean():.2f}" if view['engagement'].notna().any() else "-")

st.divider()

t_overview, t_ratings, t_concerns = st.tabs([
    "Overview",
    "Ratings Breakdown",
    "Concerns / Themes",
])

with t_overview:
    
    st.subheader("Moderator Attendance")
    mod_counts = view["moderator_name"].value_counts().rename_axis("moderator_name").reset_index(name="count")
    sorted_mods = mod_counts.sort_values("count", ascending=False)["moderator_name"].tolist()
    base = (
        alt.Chart(mod_counts)
        .transform_joinaggregate(total='sum(count)')
        .transform_calculate(
            pct='datum.count / datum.total',
            label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
        )
    )
    chart = alt.layer(
        base.mark_bar().encode(
            x=alt.X("count:Q", title="Count"),
            y=alt.Y("moderator_name:N", sort=sorted_mods),
            tooltip=[
                alt.Tooltip("moderator_name:N", title="Moderator"),
                alt.Tooltip("count:Q", title="Count"),
                alt.Tooltip("pct:Q", title="Percent", format=".0%")
            ]
        ),
        base.mark_text(align="left", baseline="middle", dx=3).encode(
            x="count:Q",
            y=alt.Y("moderator_name:N", sort=sorted_mods),
            text="label:N"
        )
    ).properties(height=350)
    st.altair_chart(chart, use_container_width=True)

    st.subheader("Metrics Distributions")
    cA, cB, cC, cD = st.columns(4)

    def dist(col: str, title: str):
        if col not in view.columns or not view[col].notna().any():
            st.info(f"No {title.lower()} data in range.")
            return
        d = view[col].round(0).value_counts().reset_index()
        d.columns = ["score", "count"]; d = d.sort_values("score")
        base = (
            alt.Chart(d)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
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
        ).properties(height=220)
        st.altair_chart(chart, use_container_width=True)

    with cA: dist("overall", "Overall")
    with cB: dist("time_allocation", "Time Allocation")
    with cC: dist("conversation_flow", "Conversation Flow")
    with cD: dist("engagement", "Engagement")

with t_ratings:
    st.subheader("Averages by Session")
    if view["session_label"].notna().any():
        melted = (
            view.melt(
                id_vars=["session_label", "date_parsed", "session_day"],
                value_vars=["overall","time_allocation","conversation_flow","engagement"],
                var_name="metric", value_name="score"
            ).dropna()
        )
        base = alt.Chart(melted).transform_calculate(
            metric_label="join(split(datum.metric, '_'), ' ')"
        )
        chart = alt.layer(
            base.mark_line(point=True).encode(
                x=alt.X(
                    "session_label:N",
                    title="Session",
                    sort=alt.EncodingSortField(field="date_parsed", op="min", order="ascending")
                ),
                y=alt.Y("mean(score):Q", title="Average score", scale=alt.Scale(domain=[3.6, 5])),
                color=alt.Color("metric_label:N", legend=alt.Legend(title="Metric")),
                tooltip=[
                    "session_label",
                    alt.Tooltip("mean(score):Q", title="Average", format=".2f"),
                    alt.Tooltip("count():Q", title="Responses"),
                    alt.Tooltip("metric_label:N", title="Metric"),
                    "session_day"
                ]
            ),
            base.mark_text(align="center", baseline="bottom", dy=-8).encode(
                x=alt.X(
                    "session_label:N",
                    sort=alt.EncodingSortField(field="date_parsed", op="min", order="ascending")
                ),
                y=alt.Y("mean(score):Q", scale=alt.Scale(domain=[3.6, 5])),
                color="metric_label:N",
                text=alt.Text("mean(score):Q", format=".2f")
            )
        ).properties(height=360)
        st.altair_chart(chart, use_container_width=True)
    else:
        st.info("No sessions to plot.")

with t_concerns:
    st.subheader("Raised Concerns")
    st.dataframe(
        view[["moderator_name","session","concerns"]]
            .sort_values("session", ascending=False)
            .dropna(subset=["concerns"]),
        use_container_width=True,
        height=420
    )


