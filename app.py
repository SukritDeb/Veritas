# app.py
# ═══════════════════════════════════════════════════════
# VERITAS-AGENT — STREAMLIT WEB APP
#
# Run with:  streamlit run app.py
# ═══════════════════════════════════════════════════════

import sys
import os
import json
import time
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import streamlit as st
from agents.researcher   import run_researcher
from agents.fact_checker import run_fact_checker
from agents.editor       import run_editor


# ── PAGE CONFIG ─────────────────────────────────────────
# Must be the FIRST streamlit call in the file
st.set_page_config(
    page_title = "Veritas-Agent",
    page_icon  = "🔍",
    layout     = "wide"
)


# ── CUSTOM CSS ──────────────────────────────────────────
st.markdown("""
<style>
    /* Main background */
    .stApp { background-color: #0f1117; }

    /* Headline input box */
    .stTextInput > div > div > input {
        background-color : #1e2130;
        color            : #ffffff;
        border           : 1px solid #3d4460;
        border-radius    : 8px;
        font-size        : 16px;
        padding          : 12px;
    }

    /* Verdict badge */
    .verdict-badge {
        display         : inline-block;
        padding         : 8px 20px;
        border-radius   : 20px;
        font-weight     : bold;
        font-size       : 18px;
        margin          : 10px 0;
    }
    .verdict-VERIFIED    { background:#1a472a; color:#4ade80; }
    .verdict-FALSE       { background:#4a1a1a; color:#f87171; }
    .verdict-MISLEADING  { background:#4a3a1a; color:#fbbf24; }
    .verdict-UNVERIFIED  { background:#1a2a4a; color:#60a5fa; }
    .verdict-DEVELOPING  { background:#2a3a4a; color:#67e8f9; }

    /* Tweet cards */
    .tweet-card {
        background    : #1e2130;
        border        : 1px solid #3d4460;
        border-radius : 12px;
        padding       : 20px;
        margin        : 10px 0;
        font-size     : 16px;
        line-height   : 1.6;
        color         : #ffffff;
    }

    /* Confidence bar label */
    .conf-label {
        font-size   : 14px;
        color       : #9ca3af;
        margin-top  : 4px;
    }

    /* Step status cards */
    .step-card {
        background    : #1e2130;
        border-radius : 10px;
        padding       : 14px 18px;
        margin        : 6px 0;
        border-left   : 4px solid #3d4460;
    }
    .step-running { border-left-color: #fbbf24; }
    .step-done    { border-left-color: #4ade80; }
    .step-failed  { border-left-color: #f87171; }

    /* Source pills */
    .source-pill {
        display         : inline-block;
        background      : #2a2f45;
        border-radius   : 20px;
        padding         : 4px 12px;
        margin          : 4px;
        font-size       : 12px;
        color           : #9ca3af;
    }

    /* Hide Streamlit default header */
    #MainMenu {visibility: hidden;}
    footer     {visibility: hidden;}
</style>
""", unsafe_allow_html=True)


# ── HELPER FUNCTIONS ────────────────────────────────────

def verdict_color(verdict: str) -> str:
    """Returns a color hex for the confidence bar."""
    return {
        "VERIFIED"  : "#4ade80",
        "FALSE"     : "#f87171",
        "MISLEADING": "#fbbf24",
        "UNVERIFIED": "#60a5fa",
        "DEVELOPING": "#67e8f9"
    }.get(verdict, "#9ca3af")


def verdict_emoji(verdict: str) -> str:
    return {
        "VERIFIED"  : "✅",
        "FALSE"     : "❌",
        "MISLEADING": "⚠️",
        "UNVERIFIED": "🔍",
        "DEVELOPING": "🔄"
    }.get(verdict, "📋")


def save_to_json(headline, researcher_out, fact_checker_out, editor_out):
    """Save results to outputs/ folder."""
    os.makedirs("outputs", exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"outputs/result_{timestamp}.json"

    result = {
        "timestamp"         : timestamp,
        "headline"          : headline,
        "verdict"           : fact_checker_out["verdict"],
        "confidence"        : fact_checker_out["confidence_score"],
        "tweets"            : {
            "tweet_1"       : editor_out["tweet_1"],
            "tweet_2"       : editor_out["tweet_2"],
            "tweet_3"       : editor_out["tweet_3"],
        },
        "sources_used"      : [a["url"] for a in researcher_out["raw_articles"]],
        "fact_check_report" : fact_checker_out["fact_check_report"]
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return filename, result


# ── MAIN APP ────────────────────────────────────────────

def main():

    # ── HEADER ────────────────────────────────────────
    st.markdown("""
        <h1 style='text-align:center; color:#60a5fa; 
                   font-size:3em; margin-bottom:0;'>
            🔍 Veritas-Agent
        </h1>
        <p style='text-align:center; color:#9ca3af; 
                  font-size:1.1em; margin-top:8px;'>
            AI-Powered News Verification System
        </p>
        <hr style='border-color:#3d4460; margin:20px 0;'>
    """, unsafe_allow_html=True)

    # ── HOW IT WORKS (collapsible) ─────────────────────
    with st.expander("💡 How does this work?"):
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            **🔍 Step 1: Researcher**
            Searches the web for 5+ real articles
            about your headline using Tavily AI.
            """)
        with col2:
            st.markdown("""
            **🕵️ Step 2: Fact-Checker**
            Cross-checks every claim against the
            raw articles. Assigns a confidence score.
            """)
        with col3:
            st.markdown("""
            **✍️ Step 3: Editor**
            Writes a 3-post Twitter thread using
            only verified facts. Self-checks length.
            """)

    # ── HEADLINE INPUT ─────────────────────────────────
    st.markdown("### 📰 Enter a News Headline")

    col_input, col_btn = st.columns([5, 1])

    with col_input:
        headline = st.text_input(
            label       = "headline_input",
            placeholder = 'e.g. "BREAKING: Scientists confirm human teleportation"',
            label_visibility = "collapsed"
        )

    with col_btn:
        verify_btn = st.button(
            "🔍 Verify",
            type = "primary",
            use_container_width = True
        )

    # Example headlines for quick testing
    st.markdown("**Try an example:**")
    ex_col1, ex_col2, ex_col3 = st.columns(3)
    with ex_col1:
        if st.button("🌙 Moon cheese claim"):
            headline   = "Scientists confirm the Moon is made of cheese"
            verify_btn = True
    with ex_col2:
        if st.button("🤖 AI sentience claim"):
            headline   = "Google AI system achieves full human-level sentience"
            verify_btn = True
    with ex_col3:
        if st.button("💊 Cure cancer claim"):
            headline   = "Researchers announce complete cure for all cancers"
            verify_btn = True

    # ── RUN PIPELINE ──────────────────────────────────
    if verify_btn and headline:

        st.markdown("---")
        st.markdown("### ⚙️ Pipeline Running...")

        # Three columns for live step tracking
        step1_col, step2_col, step3_col = st.columns(3)

        with step1_col:
            step1 = st.empty()
            step1.markdown("""
                <div class='step-card step-running'>
                ⏳ <b>Researcher Agent</b><br>
                <small>Searching the web...</small>
                </div>""", unsafe_allow_html=True)

        with step2_col:
            step2 = st.empty()
            step2.markdown("""
                <div class='step-card'>
                ⬜ <b>Fact-Checker Agent</b><br>
                <small>Waiting...</small>
                </div>""", unsafe_allow_html=True)

        with step3_col:
            step3 = st.empty()
            step3.markdown("""
                <div class='step-card'>
                ⬜ <b>Editor Agent</b><br>
                <small>Waiting...</small>
                </div>""", unsafe_allow_html=True)

        # Progress bar
        progress = st.progress(0, text="Starting pipeline...")

        try:
            # ── STAGE 1: RESEARCHER ───────────────────
            t1 = time.time()
            researcher_out = run_researcher(headline)
            t1 = round(time.time() - t1, 1)

            step1.markdown(f"""
                <div class='step-card step-done'>
                ✅ <b>Researcher Agent</b><br>
                <small>Done in {t1}s — 
                {len(researcher_out['raw_articles'])} articles found</small>
                </div>""", unsafe_allow_html=True)

            progress.progress(33, text="Researcher done. Fact-checking...")

            # ── STAGE 2: FACT-CHECKER ─────────────────
            step2.markdown("""
                <div class='step-card step-running'>
                ⏳ <b>Fact-Checker Agent</b><br>
                <small>Verifying claims...</small>
                </div>""", unsafe_allow_html=True)

            t2 = time.time()
            fact_checker_out = run_fact_checker(researcher_out)
            t2 = round(time.time() - t2, 1)

            step2.markdown(f"""
                <div class='step-card step-done'>
                ✅ <b>Fact-Checker Agent</b><br>
                <small>Done in {t2}s — 
                Score: {fact_checker_out['confidence_score']}/100</small>
                </div>""", unsafe_allow_html=True)

            progress.progress(66, text="Fact-check done. Writing thread...")

            # ── STAGE 3: EDITOR ───────────────────────
            step3.markdown("""
                <div class='step-card step-running'>
                ⏳ <b>Editor Agent</b><br>
                <small>Writing thread...</small>
                </div>""", unsafe_allow_html=True)

            t3 = time.time()
            editor_out = run_editor(fact_checker_out)
            t3 = round(time.time() - t3, 1)

            step3.markdown(f"""
                <div class='step-card step-done'>
                ✅ <b>Editor Agent</b><br>
                <small>Done in {t3}s</small>
                </div>""", unsafe_allow_html=True)

            progress.progress(100, text="✅ Pipeline complete!")

            # ── RESULTS SECTION ───────────────────────
            st.markdown("---")
            st.markdown("## 📊 Results")

            verdict = fact_checker_out["verdict"]
            score   = fact_checker_out["confidence_score"]

            # Top metrics row
            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Verdict",    f"{verdict_emoji(verdict)} {verdict}")
            m2.metric("Confidence", f"{score}/100")
            m3.metric("Sources",    len(researcher_out["raw_articles"]))
            m4.metric("Time",       f"{round(t1+t2+t3, 1)}s")

            # Verdict badge + confidence bar
            st.markdown(f"""
                <div class='verdict-badge verdict-{verdict}'>
                    {verdict_emoji(verdict)} {verdict}
                </div>
            """, unsafe_allow_html=True)

            st.progress(
                score / 100,
                text=f"Confidence: {score}/100"
            )

            st.markdown("---")

            # Two column layout for tweets + details
            left_col, right_col = st.columns([3, 2])

            # ── LEFT: TWITTER THREAD ──────────────────
            with left_col:
                st.markdown("### 🐦 Twitter Thread")

                for i, key in enumerate(["tweet_1","tweet_2","tweet_3"], 1):
                    tweet     = editor_out[key]
                    char_count = len(tweet)
                    color     = "#4ade80" if char_count <= 280 else "#f87171"

                    st.markdown(f"""
                        <div class='tweet-card'>
                            {tweet}
                            <div class='conf-label' 
                                 style='color:{color}; margin-top:10px;'>
                                {char_count}/280 chars
                            </div>
                        </div>
                    """, unsafe_allow_html=True)

                # Copy-friendly text area
                with st.expander("📋 Copy all tweets as plain text"):
                    full_thread = (
                        f"{editor_out['tweet_1']}\n\n"
                        f"{editor_out['tweet_2']}\n\n"
                        f"{editor_out['tweet_3']}"
                    )
                    st.text_area(
                        "Thread text",
                        value            = full_thread,
                        height           = 200,
                        label_visibility = "collapsed"
                    )

            # ── RIGHT: FACT-CHECK DETAILS ─────────────
            with right_col:
                st.markdown("### 🕵️ Fact-Check Details")

                # Sources used
                st.markdown("**Sources Found:**")
                for article in researcher_out["raw_articles"]:
                    st.markdown(f"""
                        <span class='source-pill'>
                            🔗 {article['title'][:50]}...
                        </span>
                    """, unsafe_allow_html=True)

                st.markdown("<br>", unsafe_allow_html=True)

                # Full fact-check report (collapsible)
                with st.expander("📄 Full Fact-Check Report"):
                    st.text(fact_checker_out["fact_check_report"])

                # Queries used
                with st.expander("🔎 Search Queries Used"):
                    for q in researcher_out["queries_used"]:
                        st.markdown(f"- `{q}`")

            # ── SAVE + DOWNLOAD ───────────────────────
            st.markdown("---")
            filename, result_json = save_to_json(
                headline,
                researcher_out,
                fact_checker_out,
                editor_out
            )

            st.download_button(
                label    = "💾 Download Full Report (JSON)",
                data     = json.dumps(result_json, indent=2),
                file_name= os.path.basename(filename),
                mime     = "application/json"
            )

            st.success(f"✅ Results also saved to `{filename}`")

        except Exception as e:
            progress.empty()
            st.error(f"❌ Pipeline failed: {str(e)}")
            st.markdown("""
            **Common fixes:**
            - Check your `GROQ_API_KEY` in `.env`
            - Check your `TAVILY_API_KEY` in `.env`
            - Make sure you're running from the project root
            """)

    elif verify_btn and not headline:
        st.warning("⚠️ Please enter a headline first!")

    # ── HISTORY SIDEBAR ───────────────────────────────
    with st.sidebar:
        st.markdown("### 📁 Past Results")

        if os.path.exists("outputs"):
            files = sorted(os.listdir("outputs"), reverse=True)[:10]

            if files:
                for file in files:
                    path = f"outputs/{file}"
                    try:
                        with open(path) as f:
                            data = json.load(f)

                        verdict = data.get("verdict", "?")
                        conf    = data.get("confidence", "?")
                        ts      = data.get("timestamp", "")
                        short   = data["headline"][:40] + "..."

                        emoji   = verdict_emoji(verdict)

                        with st.expander(f"{emoji} {short}"):
                            st.markdown(f"**Verdict:** {verdict}")
                            st.markdown(f"**Confidence:** {conf}/100")
                            st.markdown(f"**Time:** {ts}")
                            st.markdown("**Tweets:**")
                            st.text(data["tweets"]["tweet_1"])
                    except Exception:
                        pass
            else:
                st.caption("No past results yet.")
        else:
            st.caption("Run a verification to see history here.")


if __name__ == "__main__":
    main()