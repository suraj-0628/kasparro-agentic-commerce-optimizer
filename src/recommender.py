import json
import os
from datetime import datetime
from dotenv import load_dotenv
import requests

load_dotenv()

# ── Rule-based recommendations (no LLM needed) ────────────────────────────────

RULE_RECOMMENDATIONS = {
    "IMAGE_MISSING": {
        "priority": 1,
        "fix": "Add at least 3 product images — front view, back view, and in-use/lifestyle shot.",
        "impact": "Images are the #1 trust signal for AI shopping agents. Without them, the product is invisible to vision-capable AI systems.",
        "effort": "LOW",
    },
    "SEO_TITLE_MISSING": {
        "priority": 2,
        "fix": "Set a custom SEO title: '[Product Name] - [Key Attribute] | [Brand]'. Example: 'Cotton Kurta Shirt - Breathable Ethnic Wear | FabricIndia'",
        "impact": "AI search agents (Google Shopping, Bing) use SEO title for snippet generation. Missing = raw title used, often poorly formatted.",
        "effort": "LOW",
    },
    "SEO_DESC_MISSING": {
        "priority": 3,
        "fix": "Write a 150-160 character SEO description summarising: what it is, who it's for, key benefit.",
        "impact": "AI commerce agents use meta description for product summaries in search results.",
        "effort": "LOW",
    },
    "DESCRIPTION_MISSING": {
        "priority": 1,
        "fix": "Write a description covering: what the product is, material/specs, who it's for, size/dimensions, care instructions.",
        "impact": "CRITICAL — AI has no context to classify, compare, or recommend this product.",
        "effort": "MEDIUM",
    },
    "DESCRIPTION_TOO_SHORT": {
        "priority": 2,
        "fix": "Expand description to at least 50 words. Include: material, dimensions, use-case, target user, key feature.",
        "impact": "Short descriptions lack the signal density AI needs for intent matching and feature extraction.",
        "effort": "LOW",
    },
    "DESCRIPTION_VAGUE": {
        "priority": 2,
        "fix": "Replace phrases like 'good quality' and 'best product' with specific attributes: materials, measurements, certifications, test results.",
        "impact": "Vague phrases are filtered as noise by AI ranking models. They add word count but zero signal.",
        "effort": "LOW",
    },
    "DESCRIPTION_MISSING_MATERIAL": {
        "priority": 2,
        "fix": "Add material composition: e.g. '100% pure cotton', 'genuine full-grain leather', 'vulcanised rubber sole'.",
        "impact": "Material is the primary filter in apparel AI queries — 'cotton shirts', 'leather bags' etc.",
        "effort": "LOW",
    },
    "DESCRIPTION_MISSING_SPECS": {
        "priority": 2,
        "fix": "Add measurable specs: battery (mAh/hours), storage (GB), weight (g/kg), dimensions (mm/cm), wattage (W).",
        "impact": "Electronics without specs cannot surface in 'best laptop under X' or comparison queries.",
        "effort": "MEDIUM",
    },
    "DESCRIPTION_SPAM_CAPS": {
        "priority": 3,
        "fix": "Remove ALL-CAPS words and excessive punctuation (!!!). Use sentence case throughout.",
        "impact": "ALL-CAPS patterns are spam signals in AI ranking models — reduces trust score.",
        "effort": "LOW",
    },
    "TAGS_MISSING": {
        "priority": 1,
        "fix": "Add 5-8 tags: product type, material, use-case, target user, occasion, color, brand style.",
        "impact": "Tags are the primary retrieval index. No tags = invisible to keyword-based AI discovery.",
        "effort": "LOW",
    },
    "TAGS_TOO_FEW": {
        "priority": 2,
        "fix": "Expand to at least 5 tags covering: category, material, use-case, gender/age target, occasion.",
        "impact": "Sparse tags narrow retrieval coverage — product misses adjacent intent queries.",
        "effort": "LOW",
    },
    "CONTRADICTION_SEASON": {
        "priority": 1,
        "fix": "Align title and description to the same season/context. If it's a winter jacket, remove all summer/beach/cool references from the description.",
        "impact": "Contradictory signals cause AI to filter the product from BOTH seasonal query sets.",
        "effort": "LOW",
    },
    "TITLE_TOO_SHORT": {
        "priority": 2,
        "fix": "Expand title to include: product type + key attribute + variant. E.g. 'Cotton Kurta Shirt - Blue, Size S-XXL'",
        "impact": "Short titles lack enough tokens for AI classification. Product type becomes ambiguous.",
        "effort": "LOW",
    },
    "TITLE_ALL_CAPS": {
        "priority": 3,
        "fix": "Rewrite title in sentence case or title case. Remove excessive punctuation.",
        "impact": "ALL-CAPS titles are demoted by AI rankers as spam-like content.",
        "effort": "LOW",
    },
    "VENDOR_MISSING": {
        "priority": 3,
        "fix": "Set the vendor/brand field. Even 'Generic' is better than empty.",
        "impact": "Brand is a provenance and trust signal used by AI agents for filtering.",
        "effort": "LOW",
    },
}

EFFORT_ORDER = {"LOW": 1, "MEDIUM": 2, "HIGH": 3}

# ── Per-product recommender ───────────────────────────────────────────────────

def recommend_for_product(product_result, perception):
    issues   = product_result["issues"]
    score    = product_result["score"]
    grade    = product_result["grade"]
    retrieval = perception["aiPerception"]["retrievalScore"]

    recommendations = []
    for issue in issues:
        code = issue["code"]
        if code in RULE_RECOMMENDATIONS:
            rec = RULE_RECOMMENDATIONS[code]
            recommendations.append({
                "issueCode":  code,
                "severity":   issue["severity"],
                "field":      issue["field"],
                "problem":    issue["message"],
                "fix":        rec["fix"],
                "impact":     rec["impact"],
                "effort":     rec["effort"],
                "priority":   rec["priority"],
            })

    # Sort by priority then effort
    recommendations.sort(key=lambda x: (x["priority"], EFFORT_ORDER.get(x["effort"], 9)))

    # Quick wins = HIGH/CRITICAL severity + LOW effort
    quick_wins = [
        r for r in recommendations
        if r["severity"] in ("HIGH", "CRITICAL") and r["effort"] == "LOW"
    ]

    return {
        "handle":          product_result["handle"],
        "title":           product_result["title"],
        "currentScore":    score,
        "grade":           grade,
        "retrievalScore":  retrieval,
        "perceivedType":   perception["aiPerception"]["perceivedType"],
        "interpretation":  perception["aiPerception"]["interpretation"],
        "totalIssues":     product_result["totalIssues"],
        "quickWins":       quick_wins[:3],
        "allRecommendations": recommendations,
        "projectedScore":  min(100, score + sum(
            15 if r["severity"] == "HIGH" else
            30 if r["severity"] == "CRITICAL" else
            8  if r["severity"] == "MEDIUM" else 3
            for r in quick_wins
        )),
    }

# ── Store-level insight generator ────────────────────────────────────────────

def generate_store_insights(report, perception_data):
    top_issues  = report["summary"]["topIssues"]
    avg_score   = report["reportMeta"]["avgQualityScore"]
    avg_retrieval = perception_data["meta"]["avgRetrievalScore"]
    ambiguous   = perception_data["summary"]["ambiguousProducts"]

    insights = []

    # Insight 1: biggest systemic problem
    if top_issues:
        top = top_issues[0]
        insights.append({
            "type":    "SYSTEMIC_ISSUE",
            "title":   f"{top['code']} affects {top['count']}/30 products",
            "detail":  f"This single issue is the biggest drag on your store's AI visibility. Fixing it store-wide would have the highest ROI.",
            "action":  RULE_RECOMMENDATIONS.get(top["code"], {}).get("fix", "Review and fix this issue across all products."),
        })

    # Insight 2: retrieval gap
    gap = avg_retrieval
    insights.append({
        "type":   "RETRIEVAL_GAP",
        "title":  f"Store retrieval score is {gap}/100 — AI agents are missing {round((1 - gap/100) * 100)}% of potential traffic",
        "detail": "Even when customers search for products you carry, AI shopping agents may not surface them due to weak metadata.",
        "action": "Prioritize: tags → descriptions → SEO titles. In that order.",
    })

    # Insight 3: ambiguity
    if ambiguous > 10:
        insights.append({
            "type":   "CLASSIFICATION_RISK",
            "title":  f"{ambiguous}/30 products are ambiguous to AI classifiers",
            "detail": "These products may be shown in wrong category pages or excluded from relevant searches entirely.",
            "action": "Ensure each product title + first sentence of description clearly states the product type.",
        })

    # Insight 4: quick win opportunity
    insights.append({
        "type":   "QUICK_WIN",
        "title":  "SEO titles and descriptions are missing store-wide",
        "detail": "30/30 products are missing SEO metadata. This is a 30-minute fix with outsized AI search impact.",
        "action": "Use Shopify bulk editor: Products → Export → edit SEO columns → reimport.",
    })

    return insights

# ── Main ──────────────────────────────────────────────────────────────────────

def recommend_for_store(report: dict, perception_data: dict) -> dict:
    """
    Generates recommendations for the entire store using the existing report and perception data.
    """
    perception_map = {p["handle"]: p for p in perception_data.get("perceptions", [])}

    product_recs = []
    for product_result in report.get("products", []):
        handle = product_result["handle"]
        perception = perception_map.get(handle, {
            "aiPerception": {
                "retrievalScore": 0,
                "perceivedType": "Unknown",
                "interpretation": "No perception data available.",
            }
        })
        product_recs.append(recommend_for_product(product_result, perception))

    # Sort by score ascending (worst first)
    product_recs.sort(key=lambda x: x["currentScore"])

    store_insights = generate_store_insights(report, perception_data)

    return {
        "roiRanking": report.get("summary", {}).get("roiRanking", []),
        "meta": {
            "generatedAt":    datetime.now().isoformat(),
            "store":          report.get("reportMeta", {}).get("store", ""),
            "avgScore":       report.get("reportMeta", {}).get("avgQualityScore", 0),
            "storeGrade":     report.get("reportMeta", {}).get("storeGrade", ""),
            "avgRetrieval":   perception_data.get("meta", {}).get("avgRetrievalScore", 0),
        },
        "storeInsights":  store_insights,
        "products":       product_recs,
    }


if __name__ == "__main__":
    with open("data/report.json", encoding="utf-8") as f:
        report = json.load(f)

    with open("data/perception.json", encoding="utf-8") as f:
        perception_data = json.load(f)

    print(f"[recommender] Generating recommendations for {len(report['products'])} products...")

    output = recommend_for_store(report, perception_data)

    with open("data/recommendations.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    # Terminal output
    print(f"\n{'='*55}")
    print(f"  STORE INSIGHTS")
    print(f"{'='*55}")
    for ins in store_insights:
        print(f"\n  [{ins['type']}]")
        print(f"  {ins['title']}")
        print(f"  → {ins['action']}")

    print(f"\n{'='*55}")
    print(f"  WORST 5 PRODUCTS (needs most work)")
    print(f"{'='*55}")
    for p in product_recs[:5]:
        print(f"\n  {p['title']}")
        print(f"  Score: {p['currentScore']}/100 ({p['grade']}) | Retrieval: {p['retrievalScore']}/100")
        print(f"  AI sees it as: {p['perceivedType']}")
        if p["quickWins"]:
            print(f"  Top fix: {p['quickWins'][0]['fix'][:80]}...")

    print(f"\n{'='*55}")
    print(f"  BEST 3 PRODUCTS (closest to good)")
    print(f"{'='*55}")
    for p in product_recs[-3:]:
        print(f"\n  {p['title']}")
        print(f"  Score: {p['currentScore']}/100 ({p['grade']}) | Retrieval: {p['retrievalScore']}/100")

    print(f"\n[recommender] Saved to data/recommendations.json")