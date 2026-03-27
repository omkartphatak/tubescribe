"""Run detailed analysis on all Starter Story videos in the DB using LM Studio.
Extracts founder-specific insights: validation, tech stack, marketing, numbers.
Uses requests directly to handle Qwen3.5 thinking mode.
"""
import requests
import json
from database import get_connection

API_URL = "http://localhost:1234/v1/chat/completions"
MODEL = "mistralai/mistral-7b-instruct-v0.3"


FOUNDER_ANALYSIS_PROMPT = """You are analyzing a YouTube video from the Starter Story channel. This video features an interview with or story about a founder/developer who built a business or app.

Use the video title, description, AND transcript together to extract the most accurate and complete information. The title and description often contain key details (founder name, business name, revenue figures) that may be unclear in the transcript alone.

VIDEO TITLE: {title}

VIDEO DESCRIPTION:
{description}

Extract ALL of the following details. If a detail is not mentioned, write "Not mentioned".

## FOUNDER PROFILE
- **Founder Name(s):**
- **Business/App Name:**
- **Business Type:** (SaaS, mobile app, marketplace, content, e-commerce, etc.)
- **Location:**
- **Background:** (previous job, education, technical skills)
- **Solo or Team:** (solopreneur or co-founders/team size)

## THE IDEA & VALIDATION
- **How they got the idea:**
- **Problem they solve:**
- **How they validated the idea:**
- **MVP timeline:** (how long to build first version)
- **Initial investment/cost:**

## TECH STACK & DEVELOPMENT
- **Tech stack:** (languages, frameworks, databases, hosting, tools)
- **No-code/low-code tools used:**
- **AI tools used:** (Cursor, ChatGPT, Claude, Copilot, etc.)
- **Development approach:** (solo dev, outsourced, vibe coding, etc.)
- **Key technical decisions:**

## MARKETING & GROWTH
- **Primary marketing channels:** (Reddit, Twitter/X, SEO, YouTube, ProductHunt, paid ads, etc.)
- **Marketing strategy details:**
- **How they got first users/customers:**
- **Growth tactics that worked:**
- **Content strategy:**

## REVENUE & NUMBERS
- **Current MRR/revenue:**
- **Revenue model:** (subscription, one-time, freemium, ads, etc.)
- **Pricing:**
- **Number of users/customers:**
- **Growth timeline:** (time from launch to current revenue)
- **Profit margins:**
- **Other notable metrics:**

## KEY LESSONS & ADVICE
- **Biggest mistakes/failures:**
- **Key lessons learned:**
- **Advice for aspiring founders:**
- **What they would do differently:**

## NOTABLE QUOTES
Extract 3-5 of the most insightful, memorable, or impactful direct quotes from the founder. Choose quotes that capture their mindset, key advice, or surprising insights. Format each as:
- "Exact quote here" — context of when/why they said it

Be specific and use exact numbers, names, and details from the transcript. Do NOT make up information or quotes.

TRANSCRIPT:
{transcript}"""


def truncate(text, max_chars=12000):
    if len(text) <= max_chars:
        return text
    return text[:max_chars] + "\n\n[Transcript truncated...]"


def analyze_one(transcript, title="", description=""):
    """Run founder-focused analysis on one video using Mistral."""
    desc_truncated = (description or "No description available")[:2000]
    prompt = FOUNDER_ANALYSIS_PROMPT.format(
        title=title or "Unknown",
        description=desc_truncated,
        transcript=truncate(transcript),
    )

    resp = requests.post(API_URL, json={
        "model": MODEL,
        "max_tokens": 4096,
        "messages": [
            {"role": "user", "content": prompt},
        ],
    }, timeout=300)

    data = resp.json()
    return data["choices"][0]["message"].get("content", "")


def main():
    conn = get_connection()
    rows = conn.execute("""
        SELECT video_id, title, description, transcript, channel
        FROM videos
        WHERE transcript IS NOT NULL AND length(transcript) > 100
        AND (channel = 'Starter Story' OR channel = '')
        AND (analysis IS NULL OR length(analysis) < 50)
        ORDER BY processed_at ASC
    """).fetchall()
    conn.close()

    print(f"Videos to analyze: {len(rows)}\n")

    for i, row in enumerate(rows):
        vid_id = row["video_id"]
        title = row["title"]
        print(f"[{i+1}/{len(rows)}] Analyzing: {title[:65]}...", flush=True)

        try:
            analysis = analyze_one(row["transcript"], title=title, description=row["description"] or "")

            # Extract the NOTABLE QUOTES section into key_quotes column
            key_quotes = ""
            if "## NOTABLE QUOTES" in analysis:
                key_quotes = analysis.split("## NOTABLE QUOTES", 1)[1].strip()

            conn = get_connection()
            conn.execute(
                "UPDATE videos SET analysis = ?, key_quotes = ?, detail_level = 'Deep Dive' WHERE video_id = ?",
                (analysis, key_quotes, vid_id)
            )
            conn.commit()
            conn.close()
            print(f"  -> OK ({len(analysis)} chars)")
        except Exception as e:
            print(f"  -> ERROR: {e}")

    print("\nDone!")


if __name__ == "__main__":
    main()
