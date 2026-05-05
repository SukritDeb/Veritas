import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

FACT_CHECKER_SYSTEM_PROMPT = """
You are a ruthless, skeptical fact-checker at a world-class 
investigative journalism organization.

Your job is to verify claims — not to be kind, not to assume
good faith, but to find the TRUTH.

You have a strict process:

STEP 1 — CLAIM EXTRACTION:
List every specific, verifiable claim in the research report.
(e.g., "Claim: Event happened on Date X in Location Y")

STEP 2 — SOURCE VERIFICATION:
For each claim, check: is it directly supported by the raw 
articles? Mark each claim as:
  ✅ VERIFIED   — directly stated in source articles
  ⚠️  PARTIAL   — mentioned but with less detail/certainty
  ❌ UNSUPPORTED — NOT found in any source article
  🔴 CONTRADICTED — sources say the OPPOSITE

STEP 3 — INCONSISTENCY DETECTION:
Do the sources DISAGREE with each other on any facts?
List every contradiction you find between sources.

STEP 4 — CONFIDENCE SCORE:
Give an overall confidence score 0-100:
  90-100 : Strongly verified by multiple credible sources
  70-89  : Mostly verified, minor gaps
  50-69  : Mixed evidence, proceed with caution
  30-49  : Mostly unverified or contradicted
  0-29   : No credible support found

STEP 5 — FINAL VERDICT:
One of: VERIFIED / MISLEADING / FALSE / UNVERIFIED / DEVELOPING

FORMAT your response EXACTLY like this:
─────────────────────────────────────
CLAIMS ANALYSIS:
[your claim-by-claim analysis]

INCONSISTENCIES FOUND:
[list contradictions, or "None found"]

CONFIDENCE SCORE: [number]/100

FINAL VERDICT: [VERIFIED/MISLEADING/FALSE/UNVERIFIED/DEVELOPING]

REASONING:
[2-3 sentences explaining your verdict]
─────────────────────────────────────
"""


def extract_claims(research_report: str) -> str:
    """
    Pre-step: Ask the LLM to pull out just the specific claims
    from the research report before we verify them.
    
    This is called "chain of thought" — breaking complex 
    reasoning into smaller, more accurate steps.
    """

    print("Extracting verifiable claims from report...")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {
                "role": "system",
                "content": "You are a precise analyst. Extract every specific, verifiable factual claim from the given text. Number each one. Be thorough."
            },
            {
                "role": "user",
                "content": f"Extract all verifiable claims from this research report:\n\n{research_report}"
            }
        ],
        temperature=0.1,   
        max_tokens=800
    )

    return response.choices[0].message.content


def verify_claims(
    headline       : str,
    research_report: str,
    raw_articles   : list[dict],
    claims         : str
) -> str:
    """
    The main verification step.
    
    We give the LLM:
    - The original headline
    - The researcher's synthesis
    - The RAW articles (ground truth)
    - The extracted claims
    
    It cross-checks synthesis against raw articles.
    This catches hallucinations the Researcher may have added.
    """

    print("Cross-checking claims against raw sources...")
    sources_text = ""
    for i, article in enumerate(raw_articles, 1):
        sources_text += f"""
SOURCE {i}: {article['title']}
URL: {article['url']}
CONTENT: {article['content']}
{'─' * 50}
"""

    verification_prompt = f"""
ORIGINAL HEADLINE: {headline}

CLAIMS TO VERIFY:
{claims}

RESEARCHER'S SYNTHESIS (may contain errors):
{research_report}

RAW SOURCE ARTICLES (these are ground truth):
{sources_text}

Now perform your full fact-checking analysis.
Cross-check every claim against the RAW SOURCES — not the synthesis.
The synthesis might have errors. The raw sources are truth.
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": FACT_CHECKER_SYSTEM_PROMPT},
            {"role": "user",   "content": verification_prompt}
        ],
        temperature=0.1,  
        max_tokens=2000
    )

    return response.choices[0].message.content


def parse_confidence_score(fact_check_report: str) -> int:
    """
    Pulls the confidence score number out of the report text.
    Used by main.py to decide how to present results.
    """
    import re
    match = re.search(r'CONFIDENCE SCORE:\s*(\d+)/100', fact_check_report)
    if match:
        return int(match.group(1))
    return 50   # default if parsing fails


def parse_verdict(fact_check_report: str) -> str:
    """
    Pulls the final verdict word out of the report.
    """
    import re
    match = re.search(
        r'FINAL VERDICT:\s*(VERIFIED|MISLEADING|FALSE|UNVERIFIED|DEVELOPING)',
        fact_check_report
    )
    if match:
        return match.group(1)
    return "UNVERIFIED"    


def run_fact_checker(researcher_output: dict) -> dict:
    """
    THE MAIN FUNCTION — receives the Researcher's output dict
    and returns a verified fact-check dict.

    Input (from Researcher):
    {
        "headline"        : str,
        "research_report" : str,
        "raw_articles"    : list[dict],
        "queries_used"    : list[str]
    }

    Output (for Editor):
    {
        "headline"          : str,
        "fact_check_report" : str,
        "confidence_score"  : int,
        "verdict"           : str,
        "research_report"   : str   ← pass through for Editor
    }
    """

    print(f"\n{'='*60}")
    print(f"FACT-CHECKER AGENT STARTING")
    print(f"{'='*60}\n")

    headline        = researcher_output["headline"]
    research_report = researcher_output["research_report"]
    raw_articles    = researcher_output["raw_articles"]

    claims = extract_claims(research_report)

    fact_check_report = verify_claims(
        headline,
        research_report,
        raw_articles,
        claims
    )

    confidence_score = parse_confidence_score(fact_check_report)
    verdict          = parse_verdict(fact_check_report)

    print(f"\nConfidence Score : {confidence_score}/100")
    print(f"Verdict          : {verdict}")
    print(f"\nFACT-CHECKER AGENT DONE\n")

    return {
        "headline"          : headline,
        "fact_check_report" : fact_check_report,
        "confidence_score"  : confidence_score,
        "verdict"           : verdict,
        "research_report"   : research_report  
    }

if __name__ == "__main__":
    from agents.researcher import run_researcher

    headline = "BREAKING: Scientists confirm teleportation of humans achieved in secret Swiss lab"

    researcher_output = run_researcher(headline)

    fact_checker_output = run_fact_checker(researcher_output)

    print("\n" + "="*60)
    print("FACT-CHECK REPORT:")
    print("="*60)
    print(fact_checker_output["fact_check_report"])
    print("\n" + "="*60)
    print(f"CONFIDENCE : {fact_checker_output['confidence_score']}/100")
    print(f"VERDICT    : {fact_checker_output['verdict']}")