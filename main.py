# main.py
# ═══════════════════════════════════════════════════════
# VERITAS-AGENT — THE ORCHESTRATOR
#
# This is the single entry point for the entire system.
# It wires all three agents together into one pipeline.
#
# Usage:
#   python main.py
#   python main.py --headline "Your headline here"
# ═══════════════════════════════════════════════════════

import sys
import os
import time
import argparse
import json
from datetime import datetime

# Add project root to path (same fix as other agents)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from agents.researcher   import run_researcher
from agents.fact_checker import run_fact_checker
from agents.editor       import run_editor


# ── DISPLAY HELPERS ─────────────────────────────────────

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════╗
║                                                       ║
║   ██╗   ██╗███████╗██████╗ ██╗████████╗ █████╗ ███████╗║
║   ██║   ██║██╔════╝██╔══██╗██║╚══██╔══╝██╔══██╗██╔════╝║
║   ██║   ██║█████╗  ██████╔╝██║   ██║   ███████║███████╗║
║   ╚██╗ ██╔╝██╔══╝  ██╔══██╗██║   ██║   ██╔══██║╚════██║║
║    ╚████╔╝ ███████╗██║  ██║██║   ██║   ██║  ██║███████║║
║     ╚═══╝  ╚══════╝╚═╝  ╚═╝╚═╝   ╚═╝   ╚═╝  ╚═╝╚══════╝║
║                                                       ║
║          AI-Powered News Verification System         ║
╚═══════════════════════════════════════════════════════╝
    """)


def print_step(step_num: int, title: str, status: str = "RUNNING"):
    """Prints a clean step indicator during pipeline execution."""
    icons = {
        "RUNNING" : "⏳",
        "DONE"    : "✅",
        "FAILED"  : "❌",
        "SKIPPED" : "⏭️"
    }
    icon = icons.get(status, "•")
    print(f"\n{icon} STEP {step_num}/3 — {title}")
    print("─" * 50)


def print_pipeline_summary(
    headline        : str,
    researcher_out  : dict,
    fact_checker_out: dict,
    editor_out      : dict,
    total_time      : float
):
    """Prints the complete final summary after all agents finish."""

    verdict   = fact_checker_out["verdict"]
    score     = fact_checker_out["confidence_score"]

    verdict_style = {
        "VERIFIED"   : ("✅", "\033[92m"),  # green
        "MISLEADING" : ("⚠️",  "\033[93m"),  # yellow
        "FALSE"      : ("❌", "\033[91m"),  # red
        "UNVERIFIED" : ("🔍", "\033[94m"),  # blue
        "DEVELOPING" : ("🔄", "\033[96m"),  # cyan
    }
    emoji, color = verdict_style.get(verdict, ("📋", ""))
    reset = "\033[0m"

    print(f"""
{'═'*60}
                    PIPELINE COMPLETE
{'═'*60}

📰 HEADLINE:
   {headline}

{color}{emoji} VERDICT     : {verdict}{reset}
📊 CONFIDENCE : {score}/100
⏱️  TOTAL TIME : {total_time:.1f} seconds
🔗 SOURCES    : {len(researcher_out['raw_articles'])} articles used
🔎 QUERIES    : {', '.join(researcher_out['queries_used'])}

{'─'*60}
{editor_out['formatted_output']}
""")


# ── PIPELINE STAGES ─────────────────────────────────────

def stage_1_research(headline: str) -> dict | None:
    """
    Runs the Researcher Agent.
    Returns output dict or None if it fails.
    """
    print_step(1, "RESEARCHER AGENT — Searching the web")

    try:
        start   = time.time()
        output  = run_researcher(headline)
        elapsed = time.time() - start

        print_step(1, f"RESEARCHER AGENT — Done in {elapsed:.1f}s", "DONE")
        return output

    except Exception as e:
        print_step(1, f"RESEARCHER AGENT — FAILED: {e}", "FAILED")
        print(f"\n  Error details: {str(e)}")
        return None


def stage_2_fact_check(researcher_output: dict) -> dict | None:
    """
    Runs the Fact-Checker Agent.
    Returns output dict or None if it fails.
    """
    print_step(2, "FACT-CHECKER AGENT — Verifying claims")

    try:
        start   = time.time()
        output  = run_fact_checker(researcher_output)
        elapsed = time.time() - start

        print_step(2, f"FACT-CHECKER AGENT — Done in {elapsed:.1f}s", "DONE")
        return output

    except Exception as e:
        print_step(2, f"FACT-CHECKER AGENT — FAILED: {e}", "FAILED")
        print(f"\n  Error details: {str(e)}")
        return None


def stage_3_edit(fact_checker_output: dict) -> dict | None:
    """
    Runs the Editor Agent.
    Returns output dict or None if it fails.
    """
    print_step(3, "EDITOR AGENT — Writing Twitter thread")

    try:
        start   = time.time()
        output  = run_editor(fact_checker_output)
        elapsed = time.time() - start

        print_step(3, f"EDITOR AGENT — Done in {elapsed:.1f}s", "DONE")
        return output

    except Exception as e:
        print_step(3, f"EDITOR AGENT — FAILED: {e}", "FAILED")
        print(f"\n  Error details: {str(e)}")
        return None


# ── SAVE RESULTS ────────────────────────────────────────

def save_results(
    headline        : str,
    researcher_out  : dict,
    fact_checker_out: dict,
    editor_out      : dict
):
    """
    Saves the full pipeline results to a JSON file.
    Useful for reviewing past analyses.
    """

    # Create outputs/ folder if it doesn't exist
    os.makedirs("outputs", exist_ok=True)

    # Filename based on timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename  = f"outputs/result_{timestamp}.json"

    result = {
        "timestamp"   : timestamp,
        "headline"    : headline,
        "verdict"     : fact_checker_out["verdict"],
        "confidence"  : fact_checker_out["confidence_score"],
        "tweets"      : {
            "tweet_1" : editor_out["tweet_1"],
            "tweet_2" : editor_out["tweet_2"],
            "tweet_3" : editor_out["tweet_3"],
        },
        "sources_used": [
            a["url"] for a in researcher_out["raw_articles"]
        ],
        "fact_check_report": fact_checker_out["fact_check_report"]
    }

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"💾 Results saved to: {filename}")
    return filename


# ── MAIN PIPELINE ────────────────────────────────────────

def run_pipeline(headline: str, save: bool = True) -> dict | None:
    """
    THE CORE FUNCTION.
    Runs all 3 agents in sequence with error handling.

    Args:
        headline : the news headline to verify
        save     : whether to save results to JSON

    Returns:
        Final results dict, or None if pipeline failed
    """

    print_banner()

    print(f"📰 Input Headline:")
    print(f"   \"{headline}\"")
    print(f"\n🕐 Started at: {datetime.now().strftime('%H:%M:%S')}")

    total_start = time.time()

    # ── STAGE 1: RESEARCH ───────────────────────────────
    researcher_out = stage_1_research(headline)

    if researcher_out is None:
        print("\n💥 Pipeline stopped: Researcher Agent failed.")
        print("   Check your TAVILY_API_KEY in .env")
        return None

    # ── STAGE 2: FACT-CHECK ─────────────────────────────
    fact_checker_out = stage_2_fact_check(researcher_out)

    if fact_checker_out is None:
        print("\n💥 Pipeline stopped: Fact-Checker Agent failed.")
        print("   Check your GROQ_API_KEY in .env")
        return None

    # ── CONFIDENCE GATE ─────────────────────────────────
    # If confidence is extremely low, warn before continuing
    if fact_checker_out["confidence_score"] < 20:
        print("\n⚠️  WARNING: Confidence score is very low (<20)")
        print("   The Editor will proceed but results may be unreliable.")

    # ── STAGE 3: EDIT ───────────────────────────────────
    editor_out = stage_3_edit(fact_checker_out)

    if editor_out is None:
        print("\n💥 Pipeline stopped: Editor Agent failed.")
        return None

    # ── FINAL SUMMARY ───────────────────────────────────
    total_time = time.time() - total_start

    print_pipeline_summary(
        headline,
        researcher_out,
        fact_checker_out,
        editor_out,
        total_time
    )

    # ── SAVE RESULTS ────────────────────────────────────
    if save:
        save_results(
            headline,
            researcher_out,
            fact_checker_out,
            editor_out
        )

    return {
        "researcher"  : researcher_out,
        "fact_checker": fact_checker_out,
        "editor"      : editor_out
    }


# ── ENTRY POINT ─────────────────────────────────────────

def get_headline_from_user() -> str:
    """Interactive prompt if no headline passed via CLI."""
    print("\n" + "─"*60)
    print("Enter a news headline to verify.")
    print("─"*60)
    headline = input("📰 Headline: ").strip()

    if not headline:
        print("❌ No headline entered. Exiting.")
        sys.exit(1)

    return headline


if __name__ == "__main__":

    # ── ARGUMENT PARSER ─────────────────────────────────
    # Lets you run:  python main.py --headline "some news"
    # Or just:       python main.py   (interactive mode)

    parser = argparse.ArgumentParser(
        description="Veritas-Agent: AI News Verification System"
    )
    parser.add_argument(
        "--headline",
        type=str,
        help="The news headline to verify",
        default=None
    )
    parser.add_argument(
        "--no-save",
        action="store_true",
        help="Don't save results to JSON file",
        default=False
    )

    args = parser.parse_args()

    # Get headline from CLI arg or interactive input
    if args.headline:
        headline = args.headline
    else:
        headline = get_headline_from_user()

    # Run the pipeline!
    run_pipeline(headline, save=not args.no_save)