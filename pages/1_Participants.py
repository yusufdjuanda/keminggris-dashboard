import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from datetime import datetime

# ---------------------------------
# Page Config
# ---------------------------------
st.set_page_config(
    page_title="Keminggris Dashboard | Participants",
    page_icon="👥",
    layout="wide",
)

# ---------------------------------
# Data Loader
# ---------------------------------
@st.cache_data(show_spinner=False)
def load_participants(file):
    df = pd.read_csv(file)

    # Normalize columns (supports capitalized & lowercase headers)
    rename_map = {
        'Timestamp': 'timestamp',
        'Name': 'name',
        'Email': 'email',
        'Sessions Joining': 'sessions_joining',
        'English Level': 'english_level',
        'Motivation': 'motivation',
        'Instagram': 'instagram',
        'Discovery Source': 'discovery_source',
        'Topic Suggestion': 'topic_suggestion',
        'Email Address': 'email_address',
        'Session Type': 'session_type',
    }
    for k, v in list(rename_map.items()):
        if k.lower() in df.columns:
            rename_map[k.lower()] = v
    present = {k: v for k, v in rename_map.items() if k in df.columns}
    if present:
        df = df.rename(columns=present)

    # Ensure key columns exist
    for col in [
        "timestamp","name","email","sessions_joining","english_level","motivation",
        "instagram","discovery_source","topic_suggestion","email_address","session_type"
    ]:
        if col not in df.columns:
            df[col] = np.nan

    # Parse timestamp + helpers
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    df["date"] = df["timestamp"].dt.date
    df["month"] = df["timestamp"].dt.to_period("M").astype(str)

    # Cleaning
    for c in ["name","email","email_address","english_level","discovery_source","session_type","motivation"]:
        df[c] = df[c].astype(str).str.strip()

    # Identity columns
    df["participant_email"] = df["email"].where(
        df["email"].notna() & (df["email"].str.len() > 0),
        df["email_address"]
    )
    df["participant_key"] = df["participant_email"].fillna(df["instagram"]).fillna(df["name"]).str.lower().str.strip()
    df["display_name"] = df["name"].where(df["name"].str.len() > 0, df["participant_email"])

    # Normalize session type to {Regular, Friday, Other}
    st_lower = df["session_type"].str.lower().fillna("")
    df["session_type_norm"] = np.where(
        st_lower.str.contains("friday"), "Friday",
        np.where(st_lower.str.contains("regular"), "Regular", "Other")
    )

    df = df.dropna(subset=['name'])

    df["sessions_count"] = int(1)
    return df

# ---------------------------------
# Data Source (no uploader; always from script path)
# ---------------------------------
DATA_PATH = "participants.csv"
data = load_participants(DATA_PATH)

# ---------------------------------
# Filters
#   - Sidebar: date, English level, discovery source
#   - Page toggles: session type (All/Regular/Friday), row mode (All signups / Unique participants)
# ---------------------------------
st.sidebar.header("Filters")

session_pick = st.sidebar.radio(
    "Session filter",
    ["All", "Regular", "Friday"],
    index=0,           # default to "All"
    horizontal=False,  # radios stack vertically in the sidebar
    key="session_pick"
)

mode_pick = st.sidebar.radio(
    "Rows",
    ["All signups", "Unique participants"],
    index=0,           # default to "All signups"
    horizontal=False,
    key="row_mode"
)
view = data.copy()

if session_pick != "All":
    view = view[view["session_type_norm"] == session_pick]

if mode_pick.startswith("Unique"):
    # keep FIRST record per email (earliest timestamp)
    view = view.sort_values(["participant_key", "timestamp"], na_position="last") \
                         .drop_duplicates("participant_key", keep="first")


# ---------------------------------
# Header & KPIs
# ---------------------------------
LOGO_PATH = "assets/KEMINGGRIS LOGO HD Horizontal.png"
try:
    st.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass
st.title("👥 Participants | Keminggris Dashboard")
st.caption("Explore participant demographics. Use the filters to focus your view.")

k1, k2, k3, k4 = st.columns(4)
with k1:
    st.metric("All Signups", f"{view.shape[0]:,}")
with k2:
    st.metric("Unique participants", f"{view['participant_key'].nunique():,}")
with k3:
    st.metric("Total Sessions", int(view["sessions_joining"].value_counts().shape[0]))
with k4:
    mode_lv = view["english_level"].mode(dropna=True)
    st.metric("Top English level Participants", mode_lv.iloc[0] if not mode_lv.empty else "-")

# ---------------------------------
# Tabs (Signup Trends removed; Motivation added)
# ---------------------------------
t_overview, t_motivation, t_sessions = st.tabs([
    "Overview",
    "Motivation",
    "Attendance",
])

with t_overview:
    cA, colSep, cB = st.columns([1.2, 0.01, 3])
    with cB:
            st.subheader("Where did the participants hear about Keminggris?")
            # Discovery source donut
            
            if view["discovery_source"].notna().any():
                src = (
                    view.assign(discovery_source=view["discovery_source"].fillna("Unknown"))
                        .groupby("discovery_source").size().reset_index(name="count").sort_values("count", ascending=False)
                )
                st.altair_chart(
                    alt.Chart(src).mark_arc(innerRadius=90).encode(
                        theta="count:Q",
                        color=alt.Color(
                            "discovery_source:N",
                            sort=alt.SortField(field="count", order="descending"),
                            legend=alt.Legend(title="Source")
                        ),
                        tooltip=["discovery_source", "count"],
                    ).properties(height=320),
                    use_container_width=True
                )
    with colSep:
        st.markdown(
        "<div style='height: 400px; border-left: 1px solid #ddd; margin: 0 0.5px;'></div>",
        unsafe_allow_html=True
    )
    with cA:
            st.subheader("\tSession Type")
            # Session type bar (normalized)
            stype_df = (
                view.assign(session_type_norm=view["session_type_norm"].fillna("Other"))
                    .groupby("session_type_norm").size().reset_index(name="count")
                    .sort_values("count", ascending=False)
            )
            st.altair_chart(
                alt.Chart(stype_df).mark_bar().encode(
                    x=alt.X("session_type_norm:N", sort="-y", title="Session type"),
                    y=alt.Y("count:Q", title="Participants"),
                    tooltip=["session_type_norm", "count"],
                ).properties(height=320),
                use_container_width=True
            )
    st.subheader("English Level")
    st.write("Distribution of self-reported English levels for the participants.")

    # English level bar
    if view["english_level"].notna().any():
        lvl = (
            view.assign(english_level=view["english_level"].fillna("Unknown"))
                .groupby("english_level").size().reset_index(name="count")
                .sort_values("count", ascending=False)
        )
        sorted_lvls = lvl.sort_values("count", ascending=False)["english_level"].tolist()
        base = (
            alt.Chart(lvl)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart = alt.layer(
            base.mark_bar().encode(
                x=alt.X("count:Q", title="Participants"),
                y=alt.Y("english_level:N", sort=sorted_lvls, title="English level"),
                tooltip=[
                    alt.Tooltip("english_level:N", title="English level"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("pct:Q", title="Percent", format=".0%")
                ]
            ),
            base.mark_text(align="left", baseline="middle", dx=3).encode(
                x="count:Q",
                y=alt.Y("english_level:N", sort=sorted_lvls),
                text="label:N"
            )
        ).properties(height=320)
        st.altair_chart(chart, use_container_width=True)

    

with t_motivation:
    st.subheader("Motivation")
    st.write("Why participants join.")
    if view["motivation"].notna().any():
        mot = (
            view.assign(motivation=view["motivation"].replace({"nan": np.nan}).fillna("Unknown"))
                .groupby("motivation").size().reset_index(name="count")
                .sort_values("count", ascending=False).head(20)
        )
        sorted_mots = mot.sort_values("count", ascending=False)["motivation"].tolist()
        base = (
            alt.Chart(mot)
            .transform_joinaggregate(total='sum(count)')
            .transform_calculate(
                pct='datum.count / datum.total',
                label="format(datum.count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
            )
        )
        chart = alt.layer(
            base.mark_bar().encode(
                x=alt.X("count:Q", title="Participants"),
                y=alt.Y(
                    "motivation:N",
                    sort=sorted_mots,
                    axis=alt.Axis(title="Motivation (Top 20)", labelLimit=200, labelPadding=8)
                ),
                tooltip=[
                    alt.Tooltip("motivation:N", title="Motivation"),
                    alt.Tooltip("count:Q", title="Count"),
                    alt.Tooltip("pct:Q", title="Percent", format=".0%")
                ]
            ),
            base.mark_text(align="left", baseline="middle", dx=3).encode(
                x="count:Q",
                y=alt.Y("motivation:N", sort=sorted_mots),
                text="label:N"
            )
        ).properties(height=480)
        st.altair_chart(chart, use_container_width=True)

with t_sessions:
    st.subheader("Top Participants by Sessions (Names)")
    st.write("Respects current filters and uniqueness mode.")
    base_for_top = view.copy()
    top_people = (
        base_for_top.groupby(["participant_key", "display_name"])["sessions_count"]
        .sum().reset_index()
        .sort_values("sessions_count", ascending=False)
        .head(10)
    )
    st.altair_chart(
        alt.layer(
            alt.Chart(top_people)
                .transform_joinaggregate(total='sum(sessions_count)')
                .transform_calculate(
                    pct='datum.sessions_count / datum.total',
                    label="format(datum.sessions_count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
                )
                .mark_bar()
                .encode(
                    x=alt.X("sessions_count:Q", title="Sessions (sum)"),
                    y=alt.Y(
                        "display_name:N",
                        sort="-x",
                        axis=alt.Axis(title="Participant", labelLimit=200, labelPadding=8)
                    ),
                    tooltip=[
                        alt.Tooltip("display_name:N", title="Participant"),
                        alt.Tooltip("sessions_count:Q", title="Sessions"),
                        alt.Tooltip("pct:Q", title="Percent", format=".0%")
                    ],
                ),
            alt.Chart(top_people)
                .transform_joinaggregate(total='sum(sessions_count)')
                .transform_calculate(
                    pct='datum.sessions_count / datum.total',
                    label="format(datum.sessions_count, ',d') + ' (' + format(datum.pct, '.0%') + ')'"
                )
                .mark_text(align="left", baseline="middle", dx=3)
                .encode(
                    x="sessions_count:Q",
                    y=alt.Y("display_name:N", sort="-x"),
                    text="label:N"
                )
        ).properties(height=320),
        use_container_width=True
    )

# Optional: peek at rows
# with st.expander("Peek raw filtered rows"):
#     st.dataframe(data, use_container_width=True)
