"""Generate a comprehensive insights report from all Starter Story analyses."""
import json
import re
from database import get_connection


def get_all_analyses():
    conn = get_connection()
    rows = conn.execute("""
        SELECT title, analysis, video_id FROM videos
        WHERE channel = 'Starter Story'
        AND analysis IS NOT NULL AND length(analysis) > 100
        ORDER BY title
    """).fetchall()
    conn.close()
    return rows


def extract_section(text, header):
    """Extract content under a markdown header."""
    pattern = rf'\*?\*?{re.escape(header)}\*?\*?(.*?)(?=\n\*?\*?[A-Z]|\Z)'
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def extract_field(text, field):
    """Extract a specific field value from analysis text."""
    pattern = rf'[-*]*\s*\*?\*?{re.escape(field)}:?\*?\*?\s*:?\s*(.*?)(?:\n[-*]|\n\n|\Z)'
    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        val = match.group(1).strip()
        if val.lower() in ('not mentioned', 'n/a', 'not specified', ''):
            return None
        return val
    return None


def parse_revenue(text):
    """Try to extract numeric revenue from text like '$17K/Month' or '$250,000/month'."""
    if not text:
        return None
    text = text.replace(',', '')
    match = re.search(r'\$(\d+(?:\.\d+)?)\s*[kK]', text)
    if match:
        return float(match.group(1)) * 1000
    match = re.search(r'\$(\d+(?:\.\d+)?)\s*[mM]', text)
    if match:
        return float(match.group(1)) * 1000000
    match = re.search(r'\$(\d+(?:,\d+)*)', text)
    if match:
        return float(match.group(1).replace(',', ''))
    return None


def main():
    rows = get_all_analyses()
    print(f"Total analyzed videos: {len(rows)}\n")

    businesses = []
    for row in rows:
        title = row["title"]
        analysis = row["analysis"]
        vid_id = row["video_id"]

        biz = {
            "title": title,
            "video_id": vid_id,
            "founder": extract_field(analysis, "Founder Name"),
            "business_name": extract_field(analysis, "Business/App Name"),
            "business_type": extract_field(analysis, "Business Type"),
            "location": extract_field(analysis, "Location"),
            "background": extract_field(analysis, "Background"),
            "solo_or_team": extract_field(analysis, "Solo or Team"),
            "idea_source": extract_field(analysis, "How they got the idea"),
            "problem": extract_field(analysis, "Problem they solve"),
            "validation": extract_field(analysis, "How they validated the idea"),
            "mvp_timeline": extract_field(analysis, "MVP timeline"),
            "initial_cost": extract_field(analysis, "Initial investment/cost"),
            "tech_stack": extract_field(analysis, "Tech stack"),
            "nocode_tools": extract_field(analysis, "No-code/low-code tools"),
            "ai_tools": extract_field(analysis, "AI tools used"),
            "dev_approach": extract_field(analysis, "Development approach"),
            "marketing_channels": extract_field(analysis, "Primary marketing channels"),
            "first_users": extract_field(analysis, "How they got first users"),
            "growth_tactics": extract_field(analysis, "Growth tactics that worked"),
            "revenue": extract_field(analysis, "Current MRR/revenue"),
            "revenue_model": extract_field(analysis, "Revenue model"),
            "pricing": extract_field(analysis, "Pricing"),
            "num_users": extract_field(analysis, "Number of users/customers"),
            "growth_timeline": extract_field(analysis, "Growth timeline"),
            "mistakes": extract_field(analysis, "Biggest mistakes/failures"),
            "lessons": extract_field(analysis, "Key lessons learned"),
            "advice": extract_field(analysis, "Advice for aspiring founders"),
        }
        businesses.append(biz)

    # === GENERATE REPORT ===
    report = []
    report.append("# Starter Story YouTube Channel — Comprehensive Founder Insights Report")
    report.append(f"\n*Based on analysis of {len(businesses)} videos*\n")

    # --- Business Types ---
    report.append("## 1. Business Types Featured")
    type_counts = {}
    for b in businesses:
        bt = (b["business_type"] or "Unknown").strip().lower()
        # Normalize
        if "saas" in bt:
            bt = "SaaS"
        elif "e-commerce" in bt or "ecommerce" in bt:
            bt = "E-commerce"
        elif "mobile app" in bt or "app" in bt:
            bt = "Mobile App"
        elif "marketplace" in bt:
            bt = "Marketplace"
        elif "content" in bt or "newsletter" in bt or "media" in bt:
            bt = "Content/Media"
        elif "agency" in bt or "service" in bt or "consulting" in bt or "freelanc" in bt:
            bt = "Agency/Services"
        elif "course" in bt or "education" in bt:
            bt = "Education/Courses"
        elif "physical" in bt or "product" in bt:
            bt = "Physical Products"
        else:
            bt = bt.title()
        type_counts[bt] = type_counts.get(bt, 0) + 1
    for bt, count in sorted(type_counts.items(), key=lambda x: -x[1]):
        report.append(f"- **{bt}**: {count} businesses")

    # --- Revenue Analysis ---
    report.append("\n## 2. Revenue & Numbers")
    revenues = []
    revenue_details = []
    for b in businesses:
        rev = parse_revenue(b["revenue"])
        if rev and rev > 0:
            revenues.append(rev)
            revenue_details.append((b["business_name"] or b["title"], rev, b["revenue"]))

    revenue_details.sort(key=lambda x: -x[1])
    if revenues:
        report.append(f"\n**Revenue data available for {len(revenues)} businesses:**")
        report.append(f"- Median monthly revenue: **${int(sorted(revenues)[len(revenues)//2]):,}**")
        report.append(f"- Average monthly revenue: **${int(sum(revenues)/len(revenues)):,}**")
        report.append(f"- Range: ${int(min(revenues)):,} — ${int(max(revenues)):,}")
        report.append("\n### Top Revenue Businesses")
        for name, rev, raw in revenue_details[:15]:
            report.append(f"- **{name}**: {raw}")

    # --- Revenue Models ---
    report.append("\n### Revenue Models")
    model_counts = {}
    for b in businesses:
        rm = b["revenue_model"]
        if rm:
            rm_lower = rm.lower()
            if "subscription" in rm_lower or "recurring" in rm_lower:
                key = "Subscription/Recurring"
            elif "one-time" in rm_lower or "one time" in rm_lower:
                key = "One-time purchase"
            elif "freemium" in rm_lower:
                key = "Freemium"
            elif "ads" in rm_lower or "advertising" in rm_lower:
                key = "Advertising"
            elif "affiliate" in rm_lower:
                key = "Affiliate"
            else:
                key = rm[:50]
            model_counts[key] = model_counts.get(key, 0) + 1
    for rm, count in sorted(model_counts.items(), key=lambda x: -x[1]):
        report.append(f"- **{rm}**: {count} businesses")

    # --- Tech Stack ---
    report.append("\n## 3. Tech Stack & Development")
    tech_mentions = {}
    tech_keywords = [
        "React", "Next.js", "NextJS", "Vue", "Angular", "Svelte",
        "Node", "Python", "Django", "Flask", "Ruby", "Rails",
        "PHP", "Laravel", "WordPress",
        "Swift", "Flutter", "React Native", "Kotlin",
        "PostgreSQL", "Postgres", "MongoDB", "MySQL", "Supabase", "Firebase",
        "AWS", "Vercel", "Heroku", "DigitalOcean", "Netlify", "Railway",
        "Stripe", "Tailwind", "TypeScript", "JavaScript",
        "Bubble", "Webflow", "Shopify", "Framer", "Carrd",
        "OpenAI", "ChatGPT", "Claude", "Cursor", "Copilot", "GPT",
        "No-code", "Low-code",
    ]
    for b in businesses:
        stack = (b["tech_stack"] or "") + " " + (b["nocode_tools"] or "") + " " + (b["ai_tools"] or "")
        stack_lower = stack.lower()
        seen = set()
        for kw in tech_keywords:
            if kw.lower() in stack_lower and kw.lower() not in seen:
                tech_mentions[kw] = tech_mentions.get(kw, 0) + 1
                seen.add(kw.lower())

    report.append("\n### Most Mentioned Technologies")
    for tech, count in sorted(tech_mentions.items(), key=lambda x: -x[1])[:25]:
        report.append(f"- **{tech}**: {count} mentions")

    # --- AI Tools ---
    report.append("\n### AI & No-Code Tools")
    ai_examples = []
    for b in businesses:
        if b["ai_tools"] and "not mentioned" not in b["ai_tools"].lower():
            ai_examples.append((b["business_name"] or b["title"], b["ai_tools"]))
    report.append(f"\n**{len(ai_examples)} businesses mentioned using AI tools:**")
    for name, tools in ai_examples[:20]:
        report.append(f"- **{name}**: {tools}")

    # --- Dev Approach ---
    report.append("\n### Development Approaches")
    dev_counts = {"Solo developer": 0, "Outsourced": 0, "Co-founder/Team": 0, "No-code": 0, "Vibe coding/AI-assisted": 0}
    for b in businesses:
        da = (b["dev_approach"] or "").lower()
        if "solo" in da:
            dev_counts["Solo developer"] += 1
        if "outsourc" in da:
            dev_counts["Outsourced"] += 1
        if "team" in da or "co-found" in da:
            dev_counts["Co-founder/Team"] += 1
        if "no-code" in da or "no code" in da:
            dev_counts["No-code"] += 1
        if "vibe" in da or "ai" in da or "cursor" in da or "chatgpt" in da:
            dev_counts["Vibe coding/AI-assisted"] += 1
    for approach, count in sorted(dev_counts.items(), key=lambda x: -x[1]):
        if count > 0:
            report.append(f"- **{approach}**: {count} businesses")

    # --- Marketing ---
    report.append("\n## 4. Marketing & Growth Strategies")
    channel_counts = {}
    channel_keywords = [
        ("SEO", ["seo", "search engine", "organic search", "google search"]),
        ("TikTok", ["tiktok"]),
        ("Twitter/X", ["twitter", " x ", "x.com"]),
        ("Reddit", ["reddit"]),
        ("YouTube", ["youtube"]),
        ("Instagram", ["instagram"]),
        ("Facebook", ["facebook"]),
        ("LinkedIn", ["linkedin"]),
        ("ProductHunt", ["producthunt", "product hunt"]),
        ("Paid Ads", ["paid ads", "google ads", "facebook ads", "ppc", "paid advertising"]),
        ("Email Marketing", ["email", "newsletter"]),
        ("Word of Mouth", ["word of mouth", "referral"]),
        ("Cold Outreach", ["cold email", "cold outreach", "cold dm"]),
        ("Content Marketing", ["content marketing", "blog", "blogging"]),
        ("Influencer", ["influencer"]),
        ("Communities", ["community", "communities", "discord", "slack"]),
        ("Partnerships", ["partner", "collaboration"]),
    ]
    for b in businesses:
        mc = (b["marketing_channels"] or "") + " " + (b["first_users"] or "") + " " + (b["growth_tactics"] or "")
        mc_lower = mc.lower()
        seen = set()
        for name, keywords in channel_keywords:
            for kw in keywords:
                if kw in mc_lower and name not in seen:
                    channel_counts[name] = channel_counts.get(name, 0) + 1
                    seen.add(name)
                    break

    report.append("\n### Most Used Marketing Channels")
    for ch, count in sorted(channel_counts.items(), key=lambda x: -x[1]):
        report.append(f"- **{ch}**: {count} businesses")

    # --- First Users ---
    report.append("\n### How Founders Got Their First Users")
    first_user_examples = []
    for b in businesses:
        if b["first_users"] and "not mentioned" not in b["first_users"].lower():
            first_user_examples.append((b["business_name"] or b["title"], b["first_users"]))
    for name, strategy in first_user_examples[:20]:
        report.append(f"- **{name}**: {strategy[:200]}")

    # --- Idea Validation ---
    report.append("\n## 5. Idea Validation Strategies")
    validation_examples = []
    for b in businesses:
        if b["validation"] and "not mentioned" not in b["validation"].lower():
            validation_examples.append((b["business_name"] or b["title"], b["validation"]))
    report.append(f"\n**{len(validation_examples)} businesses shared validation details:**")
    for name, val in validation_examples[:25]:
        report.append(f"- **{name}**: {val[:250]}")

    # --- MVP Timeline ---
    report.append("\n### MVP Build Times")
    mvp_examples = []
    for b in businesses:
        if b["mvp_timeline"] and "not mentioned" not in b["mvp_timeline"].lower():
            mvp_examples.append((b["business_name"] or b["title"], b["mvp_timeline"]))
    for name, timeline in mvp_examples[:20]:
        report.append(f"- **{name}**: {timeline[:150]}")

    # --- Founder Backgrounds ---
    report.append("\n## 6. Founder Backgrounds")
    solo_count = sum(1 for b in businesses if b["solo_or_team"] and "solo" in b["solo_or_team"].lower())
    team_count = sum(1 for b in businesses if b["solo_or_team"] and ("team" in b["solo_or_team"].lower() or "co-found" in b["solo_or_team"].lower()))
    report.append(f"- **Solopreneurs**: {solo_count}")
    report.append(f"- **Teams/Co-founders**: {team_count}")

    bg_examples = []
    for b in businesses:
        if b["background"] and "not mentioned" not in b["background"].lower():
            bg_examples.append((b["founder"] or b["business_name"] or b["title"], b["background"]))
    report.append("\n### Notable Backgrounds")
    for name, bg in bg_examples[:20]:
        report.append(f"- **{name}**: {bg[:200]}")

    # --- Lessons & Advice ---
    report.append("\n## 7. Key Lessons & Common Advice")
    lessons_list = []
    for b in businesses:
        if b["lessons"] and "not mentioned" not in b["lessons"].lower():
            lessons_list.append((b["business_name"] or b["title"], b["lessons"]))
    for name, lesson in lessons_list[:25]:
        report.append(f"- **{name}**: {lesson[:250]}")

    report.append("\n### Common Mistakes")
    mistake_list = []
    for b in businesses:
        if b["mistakes"] and "not mentioned" not in b["mistakes"].lower():
            mistake_list.append((b["business_name"] or b["title"], b["mistakes"]))
    for name, mistake in mistake_list[:20]:
        report.append(f"- **{name}**: {mistake[:250]}")

    # --- Individual Business Summaries ---
    report.append("\n## 8. Individual Business Profiles")
    for b in businesses:
        name = b["business_name"] or b["title"]
        founder = b["founder"] or "Unknown"
        rev = b["revenue"] or "Not disclosed"
        btype = b["business_type"] or "Unknown"
        report.append(f"\n### {name}")
        report.append(f"- **Founder**: {founder}")
        report.append(f"- **Type**: {btype}")
        report.append(f"- **Revenue**: {rev}")
        if b["tech_stack"]:
            report.append(f"- **Stack**: {b['tech_stack'][:150]}")
        if b["marketing_channels"]:
            report.append(f"- **Marketing**: {b['marketing_channels'][:150]}")
        if b["validation"]:
            report.append(f"- **Validation**: {b['validation'][:150]}")
        report.append(f"- **Video**: https://youtube.com/watch?v={b['video_id']}")

    final_report = "\n".join(report)
    with open("starter_story_insights_report.md", "w") as f:
        f.write(final_report)
    print(f"\nReport written to starter_story_insights_report.md ({len(final_report)} chars)")
    print(f"Covers {len(businesses)} businesses")


if __name__ == "__main__":
    main()
