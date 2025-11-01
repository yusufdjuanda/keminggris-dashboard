import streamlit as st

with open("keminggris.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

st.set_page_config(page_title="Keminggris Dashboard", page_icon="📊", layout="wide")

LOGO_PATH = "assets/KEMINGGRIS LOGO HD Horizontal.png"
try:
    st.image(LOGO_PATH, use_container_width=True)
except Exception:
    pass
st.title("📊 Keminggris Dashboard")
st.markdown("""
Interactive dashboard for analyzing feedback, engagement, and session performance from Keminggris English Club sessions.
\nUse the sidebar to switch pages:

- **👥 Participants**: demographics, discovery sources, motivation, top attendees
- **🗣️ Session Feedback**: ratings, interest to join again, suggestions
- **🧑‍🏫 Moderator Feedback**: ratings, concerns, attendance

Date updated: 01/11/2025
""")

st.divider()