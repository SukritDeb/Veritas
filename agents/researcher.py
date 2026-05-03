# agents/researcher.py
# -----------------------------------------------
# AGENT 1: THE RESEARCHER
#
# Job: Take a headline → search the web → return
#      a structured research report for the Fact-Checker
#
# It has two phases:
#   Phase 1: LLM decides the BEST search query
#   Phase 2: Tool fetches real articles
#   Phase 3: LLM summarizes findings into a report
# -----------------------------------------------

import os
import json
from dotenv import load_dotenv
from groq import Groq

# Import our search tool from the tools folder
from tools.search import search_news, format_results_for_agent

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── SYSTEM PROMPT ────────────────────────────────
# This is what makes it a "Researcher" not just any LLM
RESEARCHER_SYSTEM_PROMPT = """
You are an expert research analyst for a fact-checking organization.

Your job has TWO phases:

PHASE 1 — QUERY GENERATION:
When given a news headline, generate the 2 best search queries 
to find verifying information. Respond ONLY with JSON:
{"queries": ["query 1", "query 2"]}
No explanation. No markdown. Just the JSON.

PHASE 2 — SYNTHESIS:
When given raw articles, synthesize them into a structured report with:
- MAIN CLAIM: What the headline is actually claiming
- EVIDENCE FOR: Key facts from articles that support it
- EVIDENCE AGAINST: Facts that contradict or raise doubts
- KEY SOURCES: The most credible sources found
- VERDICT: "SUPPORTED" / "CONTRADICTED" / "UNVERIFIED" / "MIXED"

Be factual and concise. Cite article titles when referencing them.
"""


def generate_search_queries(headline: str) -> list[str]:
    """
    Phase 1: Ask the LLM what to search for.
    
    Instead of blindly searching the headline text,
    the LLM crafts SMARTER queries.
    
    Example:
    Headline: "Elon Musk buys NASA"
    Bad query: "Elon Musk buys NASA"        ← too literal
    Good query: "Elon Musk NASA acquisition 2025" ← specific
    Good query: "NASA privatization news 2025"    ← broader context
    """

    print("  🧠 Agent thinking: what should I search for?")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
            {"role": "user",   "content": f"Generate search queries for this headline: {headline}"}
        ],
        temperature=0.2,    # low — we want consistent, logical queries
        max_tokens=200
    )

    raw = response.choices[0].message.content.strip()

    # Parse the JSON the LLM returned
    try:
        parsed = json.loads(raw)
        queries = parsed["queries"]
        print(f"  🔎 Queries chosen: {queries}")
        return queries
    except json.JSONDecodeError:
        # If LLM didn't return clean JSON, fall back to the headline itself
        print("  ⚠️ JSON parse failed, using headline as fallback query")
        return [headline]


def synthesize_research(headline: str, raw_articles: str) -> str:
    """
    Phase 3: Give the LLM the raw articles and ask it
    to write a structured research report.
    """

    print("  📝 Agent synthesizing findings into report...")

    synthesis_prompt = f"""
HEADLINE TO VERIFY: {headline}

RAW ARTICLES FOUND:
{raw_articles}

Write a structured research report based on the articles above.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": RESEARCHER_SYSTEM_PROMPT},
            {"role": "user",   "content": synthesis_prompt}
        ],
        temperature=0.2,
        max_tokens=1500
    )

    return response.choices[0].message.content


def run_researcher(headline: str) -> dict:
    """
    THE MAIN FUNCTION — runs the full Researcher Agent pipeline.
    
    Input : a news headline (string)
    Output: a dict with research report + raw articles
    
    This output gets passed to the Fact-Checker Agent next.
    """

    print(f"\n{'='*60}")
    print(f"🔍 RESEARCHER AGENT STARTING")
    print(f"📰 Headline: {headline}")
    print(f"{'='*60}\n")

    # ── PHASE 1: Generate smart search queries ──
    queries = generate_search_queries(headline)

    # ── PHASE 2: Actually search the web ──────────
    all_articles = []
    for query in queries:
        articles = search_news(query, num_results=3)  # 3 per query = 6 total
        all_articles.extend(articles)

    # Remove duplicates based on URL
    seen_urls = set()
    unique_articles = []
    for article in all_articles:
        if article["url"] not in seen_urls:
            seen_urls.add(article["url"])
            unique_articles.append(article)

    print(f"  📚 Total unique articles collected: {len(unique_articles)}")

    # Format articles into text for the LLM
    formatted = format_results_for_agent(unique_articles)

    # ── PHASE 3: LLM synthesizes a report ─────────
    report = synthesize_research(headline, formatted)

    print(f"\n✅ RESEARCHER AGENT DONE\n")

    # Return everything — Fact-Checker needs both
    return {
        "headline"        : headline,
        "research_report" : report,
        "raw_articles"    : unique_articles,
        "queries_used"    : queries
    }


# -----------------------------------------------
# TEST THIS AGENT DIRECTLY
# -----------------------------------------------
if __name__ == "__main__":
    headline = "BREAKING: Scientists confirm teleportation of humans achieved in secret Swiss lab"
    
    result = run_researcher(headline)
    
    print("\n" + "="*60)
    print("📋 RESEARCH REPORT:")
    print("="*60)
    print(result["research_report"])
    print("\n" + "="*60)
    print(f"🔗 Sources used: {len(result['raw_articles'])}")
    for a in result["raw_articles"]:
        print(f"  • {a['title']}")