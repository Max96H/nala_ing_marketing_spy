"""
ING Banking Campaigns Comparator — Dashboard (final product UI)

A single Streamlit app tying together everything the pipeline produces:
  - Overview     — every scraped page, who scraped it, when
  - Positioning  — the 2D map from analysis.py (TF-IDF + PCA)
  - Radar        — the 5-dimension comparison per bank
  - Changes      — whatever watchdog.py has flagged
  - Gaps         — topics competitors use that ING doesn't
  - Chatbot      — same logic as assistant.py, embedded inline instead of a terminal

Run collector.py -> analyst.py -> analysis.py -> watchdog.py (in that order,
or via main.py) BEFORE opening this — it only reads what's already in
db/campaigns.db, it doesn't scrape or analyze anything itself.

Setup:
    pip install streamlit plotly pandas --break-system-packages
    export GROQ_API_KEY=gsk_...  (or use a .env file, see analyst.py)

Usage:
    streamlit run dashboard.py
"""

import sqlite3
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent / "src"))
import assistant  # reuse load_context() and the Groq call, don't reimplement it

load_dotenv()

DB_PATH = "db/campaigns.db"
st.set_page_config(page_title="ING Campaign Comparator", layout="wide")


def get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def table_exists(conn: sqlite3.Connection, name: str) -> bool:
    return conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone() is not None


def load_df(conn: sqlite3.Connection, table: str) -> pd.DataFrame:
    if not table_exists(conn, table):
        return pd.DataFrame()
    return pd.read_sql_query(f"SELECT * FROM {table}", conn)


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

st.title("ING Banking Campaigns Comparator")

if not Path(DB_PATH).exists():
    st.warning(f"No database found at `{DB_PATH}` yet. Run the pipeline "
               "(collector.py -> analyst.py -> analysis.py) first.")
    st.stop()

conn = get_conn()
pages_df = load_df(conn, "pages")
positioning_df = load_df(conn, "positioning")
radar_df = load_df(conn, "radar_scores")
gaps_df = load_df(conn, "gaps")
changes_df = load_df(conn, "changes")

tab_overview, tab_positioning, tab_radar, tab_changes, tab_gaps, tab_chat = st.tabs(
    ["Overview", "Positioning Map", "Radar Comparison", "Change Feed", "Gaps", "Chatbot"]
)

# --- Overview ---------------------------------------------------------------
with tab_overview:
    st.subheader("Scraped pages")
    if pages_df.empty:
        st.info("No pages scraped yet.")
    else:
        st.dataframe(
            pages_df[["bank", "page_type", "language", "scrape_date", "headline",
                      "tone", "has_numeric_offer", "scraped_by"]],
            width='stretch',
        )
        st.caption(f"{len(pages_df)} page(s) across {pages_df['bank'].nunique()} bank(s).")

# --- Positioning Map ---------------------------------------------------------
with tab_positioning:
    st.subheader("Where ING sits relative to competitors")
    if positioning_df.empty:
        st.info("No positioning data yet — run analysis.py after analyst.py.")
    else:
        fig = px.scatter(
            positioning_df, x="pca_x", y="pca_y", color="bank",
            hover_data=["page_type", "page_url"],
            title="Campaign positioning (closer = more similar tone/topics/value proposition)",
        )
        fig.update_traces(marker=dict(size=14))
        st.plotly_chart(fig, width='stretch')
        st.caption("Each point is one page. Position comes from the text similarity of its "
                   "tone, value proposition, and topics — not a literal metric, a relative one.")

# --- Radar Comparison ---------------------------------------------------------
with tab_radar:
    st.subheader("Compare banks across the 5 brief dimensions")
    if radar_df.empty:
        st.info("No radar data yet — run analysis.py after analyst.py.")
    else:
        banks = sorted(radar_df["bank"].unique())
        selected = st.multiselect("Banks to compare", banks, default=banks[:3])
        if selected:
            fig = go.Figure()
            for bank in selected:
                bank_data = radar_df[radar_df["bank"] == bank]
                fig.add_trace(go.Scatterpolar(
                    r=bank_data["score"], theta=bank_data["dimension"],
                    fill="toself", name=bank,
                ))
            fig.update_layout(polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
                               showlegend=True)
            st.plotly_chart(fig, width='stretch')
        st.caption("Scores are normalized 0-1 across banks. promo_intensity: how often a numeric "
                   "offer appears. visual_richness: average image count. colour_vibrancy: average "
                   "colour saturation. content_density: average page word count. topic_diversity: "
                   "distinct topics per page. These are measurable proxies, not the brief's "
                   "dimensions directly — worth stating plainly to the data audience.")

# --- Change Feed ---------------------------------------------------------
with tab_changes:
    st.subheader("What's changed")
    if changes_df.empty:
        st.info("No changes detected yet — needs at least two scrape runs on different dates.")
    else:
        st.dataframe(
            changes_df[["bank", "page_url", "field_changed", "previous_value",
                        "current_value", "detected_date"]].sort_values(
                "detected_date", ascending=False),
            width='stretch',
        )

# --- Gaps ---------------------------------------------------------
with tab_gaps:
    st.subheader("Topics competitors use that ING doesn't")
    if gaps_df.empty:
        st.info("No gaps computed yet — run analysis.py after analyst.py.")
    else:
        st.dataframe(gaps_df, width='stretch')
        st.caption("Candidate whitespace — a topic worth a look, not an automatic recommendation.")

# --- Chatbot ---------------------------------------------------------
with tab_chat:
    st.subheader("Ask about the data")
    if "chat_history" not in st.session_state:
        context = assistant.load_context(conn)
        st.session_state.chat_history = [
            {"role": "system", "content": f"{assistant.SYSTEM_PROMPT}\n\n{context}"}
        ]

    for msg in st.session_state.chat_history[1:]:  # skip the system message in the UI
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    question = st.chat_input("e.g. How does our tone compare to Revolut's?")
    if question:
        st.session_state.chat_history.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.write(question)

        import os
        from groq import Groq
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            st.error("Set GROQ_API_KEY (or add it to a .env file) before using the chatbot.")
        else:
            client = Groq(api_key=api_key)
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    response = client.chat.completions.create(
                        model=assistant.MODEL,
                        max_tokens=1000,
                        messages=st.session_state.chat_history,
                    )
                    answer = response.choices[0].message.content.strip()
                    st.write(answer)
            st.session_state.chat_history.append({"role": "assistant", "content": answer})

conn.close()