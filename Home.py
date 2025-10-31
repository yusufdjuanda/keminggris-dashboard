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
Welcome! Use the sidebar to switch pages:

- **👥 Participants**: demographics, discovery sources, motivation, top attendees
- **🗣️ Session Feedback**: ratings, interest to join again, suggestions
- **🧑‍🏫 Moderator Feedback**: (coming soon)

Tip: keep your CSVs next to this file:
- `participants.csv`
- `session_feedback.csv`
""")