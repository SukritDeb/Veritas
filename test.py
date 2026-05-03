# test_groq.py
# -----------------------------------------------
# LESSON 2 (Groq version): First API call
# Uses LLaMA 3 model — free, fast, no region issues
# -----------------------------------------------

import os
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(api_key=os.getenv("GROQ_API_KEY"))

SYSTEM_PROMPT = """
You are a senior news analyst with 20 years of experience.
When given a breaking news headline, you:
1. Identify what TYPE of claim it is (political, scientific, financial, etc.)
2. List 3 specific things that would need to be verified to confirm it
3. Rate the headline's credibility risk from 1-10 (10 = most likely false)

Be concise. Use bullet points. No fluff.
"""

def analyze_headline(headline: str) -> str:
    print(f"\n🔍 Analyzing: '{headline}'")
    print("⏳ Thinking...\n")

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",   # free, powerful model
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},   # agent role
            {"role": "user",   "content": headline}         # your input
        ],
        temperature=0.3,       # factual, not creative
        max_tokens=1024
    )

    # Groq follows OpenAI format — clean and standard
    return response.choices[0].message.content


if __name__ == "__main__":
    test_headline = "BREAKING: Scientists confirm teleportation of humans achieved in secret Swiss lab"

    result = analyze_headline(test_headline)
    print(result)
    print("\n" + "="*50)
    print("✅ Groq is working!")