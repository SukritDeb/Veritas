# 🔍 Veritas-Agent

> **AI-Powered News Verification System** — A multi-agent pipeline that takes a breaking news headline and autonomously verifies it using three specialized AI agents, then drafts a Twitter/X thread with only verified facts.

![Python](https://img.shields.io/badge/Python-3.10+-blue?style=flat-square&logo=python)
![Groq](https://img.shields.io/badge/LLM-Groq%20LLaMA%203.3-orange?style=flat-square)
![Tavily](https://img.shields.io/badge/Search-Tavily-green?style=flat-square)
![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-purple?style=flat-square)

---

## 📋 Table of Contents

- [What is Veritas-Agent?](#what-is-veritas-agent)
- [Live Demo](#live-demo)
- [Architecture](#architecture)
- [Agent Breakdown](#agent-breakdown)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Setup & Installation](#setup--installation)
- [Running the App](#running-the-app)
- [How It Works](#how-it-works)
- [Example Output](#example-output)
- [Deployment](#deployment)
- [Future Improvements](#future-improvements)

---

## What is Veritas-Agent?

Veritas-Agent is a **multi-agent AI system** that combats misinformation by automatically verifying breaking news headlines. Unlike a single LLM prompt, Veritas-Agent uses three **specialized AI workers** that collaborate in a pipeline — each with a distinct role, personality, and temperature setting.

**The Problem it Solves:**
- News spreads faster than it can be verified
- Manual fact-checking is slow and expensive
- A single LLM prompt is unreliable for verification (hallucinations)

**The Solution:**
- Three agents with different roles cross-check each other
- Real web search grounds responses in current sources
- A confidence score and verdict help users assess credibility instantly

---

## Live Demo

```
streamlit run app.py
```

> 🌐 Or visit the deployed version at: `https://your-username-veritas-agent.streamlit.app`

---

## Architecture

```
                        ┌─────────────────────────────────┐
                        │         USER INPUT               │
                        │   "Breaking news headline..."    │
                        └────────────────┬────────────────┘
                                         │
                                         ▼
                        ┌─────────────────────────────────┐
                        │           main.py               │
                        │        ORCHESTRATOR             │
                        │                                 │
                        │  • Controls pipeline flow       │
                        │  • Error gates between stages   │
                        │  • Confidence threshold checks  │
                        │  • Saves results to JSON        │
                        └────────────────┬────────────────┘
                                         │
                    ┌────────────────────┼────────────────────┐
                    │                    │                    │
                    ▼                    ▼                    ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │   AGENT 1        │  │   AGENT 2        │  │   AGENT 3        │
         │  Researcher      │  │  Fact-Checker    │  │   Editor         │
         │                  │  │                  │  │                  │
         │ temp=0.1         │  │ temp=0.1         │  │ temp=0.7         │
         │ (factual)        │  │ (precise)        │  │ (creative)       │
         └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                  │                     │                      │
                  ▼                     ▼                      ▼
         ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐
         │  1. LLM crafts   │  │  1. Extracts     │  │  1. Writes draft │
         │     smart queries│  │     all claims   │  │     tweet thread │
         │                  │  │                  │  │                  │
         │  2. Tavily API   │  │  2. Cross-checks │  │  2. Self-checks  │
         │     searches web │  │    vs raw sources│  │     char counts  │
         │                  │  │                  │  │                  │
         │  3. LLM writes   │  │  3. Assigns score│  │  3. Auto-fixes   │
         │     research     │  │     + verdict    │  │     long tweets  │
         │     report       │  │                  │  │                  │
         └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘
                  │                     │                     │
                  └─────────────────────┴─────────────────────┘
                                        │
                                         ▼
                        ┌─────────────────────────────────┐
                        │          FINAL OUTPUT           │
                        │                                 │
                        │  ✅ Verdict  : UNVERIFIED      │
                        │  📊 Score   : 73/100           │
                        │  🔗 Sources : 6 articles       │
                        │                                 │
                        │  Tweet 1: 🔍 We checked this... │
                        │  Tweet 2: 2/ Here's what we...  │
                        │  Tweet 3: 3/ Bottom line...      │
                        └─────────────────────────────────┘
```

---

## Agent Breakdown

### 🔍 Agent 1: The Researcher

| Property | Value |
|----------|-------|
| Temperature | `0.1` (factual) |
| Tool | Tavily Search API |
| Input | Raw headline (string) |
| Output | Research report + raw articles (dict) |

**What it does:**
1. **Phase 1 — Query Generation:** LLM crafts 2 smart search queries instead of blindly searching the headline
2. **Phase 2 — Web Search:** Tavily fetches real articles for each query (3 per query = 6 total)
3. **Phase 3 — Synthesis:** LLM reads all articles and writes a structured research report with EVIDENCE FOR, EVIDENCE AGAINST, and a preliminary VERDICT

```
Input : "BREAKING: Teleportation of humans confirmed"
Output: {
  "research_report" : "MAIN CLAIM: ... EVIDENCE FOR: ... VERDICT: UNVERIFIED",
  "raw_articles"    : [{title, url, content}, ...],
  "queries_used"    : ["human teleportation 2025", "quantum teleportation research"]
}
```

---

### 🕵️ Agent 2: The Fact-Checker

| Property | Value |
|----------|-------|
| Temperature | `0.1` (precise) |
| Tool | Chain-of-thought reasoning |
| Input | Researcher output dict |
| Output | Fact-check report + confidence score + verdict (dict) |

**What it does:**
1. **Step 1 — Claim Extraction:** Pulls every specific, verifiable claim from the research report
2. **Step 2 — Source Verification:** Cross-checks each claim against RAW articles (not the synthesis — to catch hallucinations)
3. **Step 3 — Inconsistency Detection:** Finds contradictions between sources
4. **Step 4 — Scoring:** Assigns confidence score 0-100 and a final verdict

**Verdict Options:** `VERIFIED` / `MISLEADING` / `FALSE` / `UNVERIFIED` / `DEVELOPING`

```
Input : researcher_output dict
Output: {
  "fact_check_report" : "CLAIMS ANALYSIS: ... CONFIDENCE SCORE: 73/100 ...",
  "confidence_score"  : 73,
  "verdict"           : "UNVERIFIED"
}
```

---

### ✍️ Agent 3: The Editor

| Property | Value |
|----------|-------|
| Temperature | `0.7` (creative) |
| Tool | Self-correction loop |
| Input | Fact-checker output dict |
| Output | 3-tweet thread + formatted display (dict) |

**What it does:**
1. **Phase 1 — Draft:** Writes a 3-tweet thread in brand voice using ONLY verified facts
2. **Phase 2 — Validate:** Checks character count of each tweet (max 280)
3. **Phase 3 — Self-correct:** If any tweet exceeds 280 chars, LLM trims it automatically (temperature=0.3 for editing)

**Brand Voice Rules:**
- Direct and confident
- Short punchy sentences
- Leads with most surprising fact
- Never sensationalizes
- Strategic emoji use (not excessive)

```
Input : fact_checker_output dict
Output: {
  "tweet_1" : "🔍 We fact-checked this claim...",
  "tweet_2" : "2/ Here's what sources actually say...",
  "tweet_3" : "3/ Bottom line: proceed with caution..."
}
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Language** | Python 3.10+ | Core language |
| **LLM** | Groq (LLaMA 3.3 70B) | Agent reasoning |
| **Search** | Tavily API | Real-time web search |
| **UI** | Streamlit | Web interface |
| **Config** | python-dotenv | Environment variables |
| **Serialization** | JSON | Data passing between agents |

---

## Project Structure

```
veritas-agent/
│
├── 🔑 .env                    # API keys (never commit this!)
├── 📋 .env.example            # Template for API keys
├── 🚫 .gitignore              # Ignores .env, venv/, outputs/
├── 📦 requirements.txt        # Python dependencies
│
├── 🌐 app.py                  # Streamlit web application
├── ⚙️  main.py                 # CLI orchestrator (pipeline runner)
│
├── 🤖 agents/
│   ├── __init__.py
│   ├── researcher.py          # Agent 1: Web research
│   ├── fact_checker.py        # Agent 2: Claim verification
│   └── editor.py              # Agent 3: Tweet thread writer
│
├── 🛠️  tools/
│   ├── __init__.py
│   └── search.py              # Tavily search wrapper
│
└── 💾 outputs/                # Auto-generated JSON results
    └── result_YYYYMMDD_HHMMSS.json
```

---

## Setup & Installation

### Prerequisites

- Python 3.10 or higher
- A [Groq API key](https://console.groq.com) (free)
- A [Tavily API key](https://app.tavily.com) (free — 1000 searches/month)

### Step 1: Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/veritas-agent.git
cd veritas-agent
```

### Step 2: Create Virtual Environment

```bash
# Create venv
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Mac/Linux)
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure API Keys

```bash
# Copy the example file
cp .env.example .env

# Open .env and fill in your keys
```

```bash
# .env
GROQ_API_KEY=gsk_your-groq-key-here
TAVILY_API_KEY=tvly-your-tavily-key-here
```

---

## Running the App

### Streamlit Web App (Recommended)

```bash
streamlit run app.py
```

Opens at `http://localhost:8501`

### CLI Mode

```bash
# Interactive (asks for headline)
python main.py

# Direct headline input
python main.py --headline "BREAKING: Scientists confirm teleportation"

# Without saving results
python main.py --headline "Your headline" --no-save
```

### Test Individual Agents

```bash
# Test only the Researcher
python agents/researcher.py

# Test Researcher + Fact-Checker
python agents/fact_checker.py

# Test full pipeline via Editor
python agents/editor.py
```

---

## How It Works

```
STEP 1 ── You type a headline into the web app

STEP 2 ── Researcher Agent activates
          • LLM thinks: "What should I search for?"
          • Crafts 2 optimized search queries
          • Tavily fetches 6 real web articles
          • LLM synthesizes findings into a report
          ⏱ ~10-15 seconds

STEP 3 ── Fact-Checker Agent activates
          • Extracts every verifiable claim
          • Cross-checks EACH claim vs raw articles
          • Flags: ✅ VERIFIED / ⚠️ PARTIAL / ❌ UNSUPPORTED
          • Calculates confidence score 0-100
          • Assigns final verdict
          ⏱ ~10-15 seconds

STEP 4 ── Editor Agent activates
          • Reads only VERIFIED facts
          • Writes 3-tweet thread in brand voice
          • Checks: is each tweet under 280 chars?
          • Self-corrects any that are too long
          ⏱ ~5-8 seconds

STEP 5 ── Results displayed in UI
          • Verdict badge with color coding
          • Confidence score bar
          • 3 formatted tweets with char counts
          • Source list with article titles
          • Full fact-check report (expandable)
          • Download button for JSON report
```

---

## Example Output

**Input Headline:**
```
BREAKING: Scientists confirm teleportation of humans achieved in secret Swiss lab
```

**Output:**
```
✅ VERDICT     : UNVERIFIED
📊 CONFIDENCE  : 18/100
🔗 SOURCES     : 6 articles analyzed
⏱  TOTAL TIME  : 31.4 seconds

─────────────────────────────────────────────
TWEET 1 (198 chars):
🔍 Viral claim: "Human teleportation confirmed in Swiss lab"
We fact-checked this so you don't have to. Spoiler: the 
receipts aren't there. 🧵

TWEET 2 (241 chars):
2/ What we found: Zero peer-reviewed studies. No Swiss lab 
on record. The only "teleportation" in science is quantum 
state transfer — particles, not people. Confidence: 18/100.

TWEET 3 (187 chars):
3/ Verdict: UNVERIFIED. Before sharing breaking science 
claims, check: Who published it? Is there a study link? 
Was it peer-reviewed? Stay skeptical. 🔬
─────────────────────────────────────────────
```

---

## Deployment

### Deploy to Streamlit Cloud (Free)

1. Push your code to GitHub
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Connect your GitHub repository
4. Add secrets in the Streamlit Cloud dashboard:

```toml
# Streamlit Cloud Secrets (Settings → Secrets)
GROQ_API_KEY = "gsk_your-key-here"
TAVILY_API_KEY = "tvly-your-key-here"
```

5. Click **Deploy** — your app gets a public URL instantly

> ⚠️ Make sure `outputs/` and `.env` are in `.gitignore` before pushing

---

## Future Improvements

```
SHORT TERM
──────────────────────────────────────────────
□ Let user choose brand voice (formal / Gen Z / academic)
□ Add more example headlines on the UI
□ Support non-English headlines
□ Add source credibility scoring (is it Reuters vs a blog?)

MEDIUM TERM
──────────────────────────────────────────────
□ SQLite database instead of JSON files for history
□ User accounts + saved dossiers
□ Batch mode — verify multiple headlines at once
□ Email/Slack alerts for high-risk verdicts

ADVANCED
──────────────────────────────────────────────
□ Migrate to LangGraph for dynamic agent routing
□ Add a feedback loop — users rate verdicts to improve accuracy
□ API endpoint so other apps can use Veritas-Agent
□ Real-time streaming output (watch agents think live)
```

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

Built as a learning project while studying **Generative AI and Agentic AI systems**.

> 💡 This project was built step-by-step from scratch — no LangChain, no LangGraph, just raw API calls — to deeply understand how multi-agent systems work before using frameworks that abstract the complexity away.
