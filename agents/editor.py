# agents/editor.py
# -----------------------------------------------
# AGENT 3: THE EDITOR
#
# Job: Takes verified facts from Fact-Checker and
#      writes a 3-post Twitter/X thread that is:
#      - Accurate (based on verified facts only)
#      - Engaging (people actually want to read it)
#      - On-brand (consistent voice and style)
#      - Correctly sized (≤280 chars per tweet)
# -----------------------------------------------

import sys
import os
import re
import json
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))


# ── BRAND VOICE RULES ────────────────────────────
# This is our "news verification" channel's personality.
# Tweak this to change the entire tone of output.
BRAND_VOICE = """
CHANNEL: @VeritasCheck — a trusted news verification account

VOICE RULES:
- Direct and confident, never wishy-washy
- Uses emojis strategically (not excessively)  
- Short punchy sentences. Like this. Not long rambling ones.
- Always leads with the most surprising/important fact
- Never sensationalizes — lets facts speak for themselves
- Uses "we" (as a team), not "I"
- Ends with a call to action or open question

TWEET STRUCTURE FOR FACT-CHECK THREADS:
Tweet 1 (THE HOOK)    : State the claim + our verdict. Make people stop scrolling.
Tweet 2 (THE EVIDENCE): What we found. Key facts only. Cite sources briefly.
Tweet 3 (THE TAKEAWAY): Why it matters + what to watch for. End with engagement CTA.

FORMATTING RULES:
- Each tweet MUST be under 280 characters
- Use 🧵 at end of Tweet 1 to signal thread
- Use numbers: "2/" and "3/" to mark subsequent tweets
- No hashtag spam — max 2 hashtags total across all 3 tweets
- Bold claims with CAPS sparingly
"""


# ── SYSTEM PROMPT ────────────────────────────────
EDITOR_SYSTEM_PROMPT = f"""
You are a senior social media editor at a fact-checking news organization.

{BRAND_VOICE}

CRITICAL RULES:
1. Only use facts that are VERIFIED or PARTIAL in the fact-check report
2. Never include UNSUPPORTED or CONTRADICTED claims
3. If verdict is FALSE or MISLEADING — the hook must clearly say so
4. If confidence score is below 50 — add a caveat about uncertainty
5. Every tweet must be 280 characters or fewer — COUNT carefully

Respond ONLY with valid JSON in this exact format, nothing else:
{{
  "tweet_1": "your first tweet here",
  "tweet_2": "your second tweet here", 
  "tweet_3": "your third tweet here",
  "editor_notes": "brief note on any compromises made"
}}
"""


def generate_thread_draft(
    headline         : str,
    fact_check_report: str,
    confidence_score : int,
    verdict          : str
) -> dict:
    """
    First pass: generate the raw thread draft.
    Gives the LLM full creative freedom within the rules.
    """

    print("  ✍️  Generating thread draft...")

    prompt = f"""
Write a 3-tweet thread for this verified news story:

ORIGINAL HEADLINE: {headline}

VERDICT: {verdict}
CONFIDENCE SCORE: {confidence_score}/100

FACT-CHECK REPORT:
{fact_check_report}

Follow all brand voice rules and CRITICAL RULES exactly.
Remember: each tweet must be under 280 characters.
Return only valid JSON.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": EDITOR_SYSTEM_PROMPT},
            {"role": "user",   "content": prompt}
        ],
        temperature=0.7,    # ← higher! we want creative writing
        max_tokens=1000
    )

    raw = response.choices[0].message.content.strip()

    # Clean up JSON (LLM sometimes adds markdown code fences)
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # If JSON parse fails, return a fallback structure
        print("  ⚠️  JSON parse failed — using fallback")
        return {
            "tweet_1"      : f"🔍 FACT CHECK: {headline[:200]}",
            "tweet_2"      : f"Verdict: {verdict} | Confidence: {confidence_score}/100",
            "tweet_3"      : "Full analysis in our bio link. Follow for more fact-checks.",
            "editor_notes" : "Fallback used due to JSON parse error"
        }


def validate_and_fix_tweets(thread: dict) -> dict:
    """
    Quality control step — checks character counts
    and asks LLM to fix any tweets that are too long.
    
    This is a self-correcting loop — a key agentic pattern!
    """

    print("  📏 Validating tweet lengths...")

    tweets_to_fix = {}

    for key in ["tweet_1", "tweet_2", "tweet_3"]:
        tweet = thread.get(key, "")
        char_count = len(tweet)

        if char_count > 280:
            tweets_to_fix[key] = {
                "text"    : tweet,
                "overlaps": char_count - 280
            }
            print(f"  ⚠️  {key} is {char_count} chars — needs trimming")
        else:
            print(f"  ✅ {key} is {char_count} chars — good")

    # If nothing needs fixing, return as-is
    if not tweets_to_fix:
        return thread

    # Ask LLM to fix the overlong tweets
    print("  🔧 Fixing overlong tweets...")

    fix_prompt = f"""
These tweets are too long and need to be shortened.
Keep the same meaning, same tone, same brand voice.
ONLY shorten — don't change what they say.

TWEETS TO FIX:
{json.dumps(tweets_to_fix, indent=2)}

Return ONLY valid JSON with the fixed versions:
{{"tweet_1": "...", "tweet_2": "...", "tweet_3": "..."}}
Include ALL three tweets even if only one needed fixing.
Current versions of all tweets:
{json.dumps(thread, indent=2)}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a precise copy editor. Shorten tweets to under 280 characters without changing their meaning or tone. Return only valid JSON."},
            {"role": "user",   "content": fix_prompt}
        ],
        temperature=0.3,    # lower for editing — we want precision
        max_tokens=600
    )

    raw = response.choices[0].message.content.strip()
    raw = re.sub(r"```json|```", "", raw).strip()

    try:
        fixed = json.loads(raw)
        # Merge fixes back into original thread
        thread.update(fixed)
        return thread
    except json.JSONDecodeError:
        return thread   # return original if fix also fails


def format_final_output(thread: dict, verdict: str, confidence_score: int) -> str:
    """
    Formats the thread dict into a pretty printable string.
    """

    # Verdict gets an emoji
    verdict_emoji = {
        "VERIFIED"   : "✅",
        "MISLEADING" : "⚠️",
        "FALSE"      : "❌",
        "UNVERIFIED" : "🔍",
        "DEVELOPING" : "🔄"
    }.get(verdict, "📋")

    output = f"""
╔══════════════════════════════════════════════════╗
║           VERITAS-CHECK TWITTER THREAD           ║
╚══════════════════════════════════════════════════╝

{verdict_emoji} VERDICT: {verdict}  |  📊 CONFIDENCE: {confidence_score}/100

─────────────────────────────────────────────────
TWEET 1 ({len(thread.get('tweet_1', ''))} chars):
{thread.get('tweet_1', '')}

─────────────────────────────────────────────────
TWEET 2 ({len(thread.get('tweet_2', ''))} chars):
{thread.get('tweet_2', '')}

─────────────────────────────────────────────────
TWEET 3 ({len(thread.get('tweet_3', ''))} chars):
{thread.get('tweet_3', '')}

─────────────────────────────────────────────────
📝 EDITOR NOTES: {thread.get('editor_notes', 'None')}
"""
    return output


def run_editor(fact_checker_output: dict) -> dict:
    """
    THE MAIN FUNCTION — receives Fact-Checker output,
    returns a ready-to-post Twitter thread.

    Input (from Fact-Checker):
    {{
        "headline"          : str,
        "fact_check_report" : str,
        "confidence_score"  : int,
        "verdict"           : str,
        "research_report"   : str
    }}

    Output (final product!):
    {{
        "headline"        : str,
        "tweet_1"         : str,
        "tweet_2"         : str,
        "tweet_3"         : str,
        "verdict"         : str,
        "confidence_score": int,
        "editor_notes"    : str,
        "formatted_output": str   ← ready to print/display
    }}
    """

    print(f"\n{'='*60}")
    print(f"✍️  EDITOR AGENT STARTING")
    print(f"{'='*60}\n")

    headline          = fact_checker_output["headline"]
    fact_check_report = fact_checker_output["fact_check_report"]
    confidence_score  = fact_checker_output["confidence_score"]
    verdict           = fact_checker_output["verdict"]

    # ── PHASE 1: Generate the draft ──────────────
    thread = generate_thread_draft(
        headline,
        fact_check_report,
        confidence_score,
        verdict
    )

    # ── PHASE 2: Validate + fix lengths ──────────
    # This is a self-correction loop — agent checks its own work!
    thread = validate_and_fix_tweets(thread)

    # ── PHASE 3: Format for display ──────────────
    formatted = format_final_output(thread, verdict, confidence_score)

    print(f"\n✅ EDITOR AGENT DONE\n")

    return {
        "headline"        : headline,
        "tweet_1"         : thread.get("tweet_1", ""),
        "tweet_2"         : thread.get("tweet_2", ""),
        "tweet_3"         : thread.get("tweet_3", ""),
        "verdict"         : verdict,
        "confidence_score": confidence_score,
        "editor_notes"    : thread.get("editor_notes", ""),
        "formatted_output": formatted
    }


# -----------------------------------------------
# TEST — runs all 3 agents in sequence
# -----------------------------------------------
if __name__ == "__main__":
    from agents.researcher   import run_researcher
    from agents.fact_checker import run_fact_checker

    headline = "BREAKING: Scientists confirm teleportation of humans achieved in secret Swiss lab"

    print("🚀 Running full pipeline...\n")

    # Agent 1
    researcher_output    = run_researcher(headline)

    # Agent 2
    fact_checker_output  = run_fact_checker(researcher_output)

    # Agent 3
    editor_output        = run_editor(fact_checker_output)

    # Final output
    print(editor_output["formatted_output"])