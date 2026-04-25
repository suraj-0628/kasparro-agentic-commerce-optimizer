import json
import re
from datetime import datetime

# ── Rule definitions ──────────────────────────────────────────────────────────

VAGUE_PHRASES = [
    "good quality", "best quality", "great product", "good product",
    "very good", "nice product", "best product", "high quality",
    "premium quality", "excellent quality", "top quality", "must buy",
    "buy now", "don't miss", "limited stock", "hurry up", "great quality"
]

MATERIAL_WORDS = [
    "cotton", "leather", "polyester", "silk", "wool", "nylon",
    "canvas", "denim", "linen", "rubber", "synthetic", "genuine"
]

SPEC_PATTERN = re.compile(
    r'\b\d+\s*(gb|mb|tb|hz|w|kg|g|mm|cm|inch|mah|v|hours?|hr|mp)\b', re.I
)

APPAREL_HINTS = ["clothing", "shirt", "kurta", "jacket", "shoe", "sneaker",
                 "belt", "bag", "wallet", "handbag", "apparel", "hoodie"]

ELECTRONICS_HINTS = ["laptop", "computer", "headphone", "earphone",
                     "speaker", "smartwatch", "electronics", "audio"]

SEVERITY_WEIGHTS = {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 8, "LOW": 3}

# ── Individual rule functions ─────────────────────────────────────────────────

def rule_title_missing(p):
    if not p.get("title", "").strip():
        return ("TITLE_MISSING", "CRITICAL", "title",
                "Product has no title.", None)

def rule_title_too_short(p):
    t = p.get("title", "").strip()
    if t and len(t) < 10:
        return ("TITLE_TOO_SHORT", "HIGH", "title",
                f"Title is only {len(t)} chars — too short for AI classification.", t)

def rule_title_all_caps(p):
    words = [w for w in p.get("title", "").split() if len(w) > 3]
    if words and sum(1 for w in words if w == w.upper()) / len(words) > 0.5:
        return ("TITLE_ALL_CAPS", "MEDIUM", "title",
                "Title uses excessive ALL CAPS — reads as spam to AI rankers.",
                p["title"])

def rule_description_missing(p):
    if not p.get("descriptionPlain", "").strip():
        return ("DESCRIPTION_MISSING", "CRITICAL", "description",
                "No description — AI has zero context.", None)

def rule_description_too_short(p):
    wc = p.get("descriptionWordCount", 0)
    if 0 < wc < 20:
        return ("DESCRIPTION_TOO_SHORT", "HIGH", "description",
                f"Only {wc} words in description. Minimum 20 needed for AI context.",
                p.get("descriptionPlain", "")[:100])

def rule_description_vague(p):
    desc = p.get("descriptionPlain", "").lower()
    found = [ph for ph in VAGUE_PHRASES if ph in desc]
    if found:
        return ("DESCRIPTION_VAGUE", "HIGH", "description",
                f"{len(found)} vague phrase(s) found — no signal for AI systems.",
                found)

def rule_description_no_specs(p):
    signal = (p.get("productType") or "" + " ".join(p.get("tags", []))).lower()
    is_electronics = any(h in signal for h in ELECTRONICS_HINTS)
    if not is_electronics:
        return None
    if not SPEC_PATTERN.search(p.get("descriptionPlain", "")):
        return ("DESCRIPTION_MISSING_SPECS", "MEDIUM", "description",
                "Electronics product has no measurable specs. AI cannot compare or rank it.",
                None)

def rule_description_no_material(p):
    signal = (p.get("title", "") + " " + " ".join(p.get("tags", []))).lower()
    is_apparel = any(h in signal for h in APPAREL_HINTS)
    if not is_apparel:
        return None
    desc = p.get("descriptionPlain", "").lower()
    if not any(m in desc for m in MATERIAL_WORDS):
        return ("DESCRIPTION_MISSING_MATERIAL", "MEDIUM", "description",
                "Apparel product has no material mentioned. Material is a primary AI signal.",
                None)

def rule_description_spam_caps(p):
    words = [w for w in p.get("descriptionPlain", "").split() if len(w) > 3]
    caps = [w for w in words if w == w.upper() and re.search(r'[A-Z]{2,}', w)]
    if words and len(caps) / len(words) > 0.25:
        return ("DESCRIPTION_SPAM_CAPS", "MEDIUM", "description",
                f"{len(caps)} ALL-CAPS words in description — spam signal to AI rankers.",
                caps[:5])

def rule_tags_missing(p):
    if not p.get("tags"):
        return ("TAGS_MISSING", "HIGH", "tags",
                "No tags — invisible to keyword-based AI retrieval.", None)

def rule_tags_too_few(p):
    tags = p.get("tags", [])
    if 0 < len(tags) < 3:
        return ("TAGS_TOO_FEW", "MEDIUM", "tags",
                f"Only {len(tags)} tag(s). Recommend at least 3 for AI retrieval coverage.",
                tags)

def rule_image_missing(p):
    if not p.get("hasImages"):
        return ("IMAGE_MISSING", "HIGH", "images",
                "No images — vision AI agents cannot verify this product.", None)

def rule_image_alt_missing(p):
    missing = p.get("imagesMissingAlt", 0)
    if missing > 0:
        return ("IMAGE_ALT_MISSING", "LOW", "images",
                f"{missing} image(s) missing alt text — reduces AI vision signal.", None)

def rule_seo_title_missing(p):
    if not p.get("seo", {}).get("title"):
        return ("SEO_TITLE_MISSING", "MEDIUM", "seo",
                "No SEO title — AI search agents fall back to raw product title.", None)

def rule_seo_desc_missing(p):
    if not p.get("seo", {}).get("description"):
        return ("SEO_DESC_MISSING", "LOW", "seo",
                "No SEO meta description — AI commerce agents can't generate snippets.", None)

def rule_vendor_missing(p):
    if not p.get("vendor", "").strip():
        return ("VENDOR_MISSING", "LOW", "vendor",
                "No vendor/brand — brand is a trust signal for AI provenance filtering.", None)

def rule_contradiction_season(p):
    text = (p.get("title", "") + " " + p.get("descriptionPlain", "")).lower()
    winter = ["winter", "warm", "heavy", "thermal", "insulated", "cold weather"]
    summer = ["summer", "cool", "beach", "lightweight", "hot weather", "poolside"]
    has_winter = any(w in text for w in winter)
    has_summer = any(w in text for w in summer)
    if has_winter and has_summer:
        return ("CONTRADICTION_SEASON", "HIGH", "description",
                "Conflicting seasonal signals — AI receives contradictory intent context.",
                {
                    "winter_found": [w for w in winter if w in text],
                    "summer_found": [w for w in summer if w in text]
                })

# ── Rule runner ───────────────────────────────────────────────────────────────

RULES = [
    rule_title_missing, rule_title_too_short, rule_title_all_caps,
    rule_description_missing, rule_description_too_short, rule_description_vague,
    rule_description_no_specs, rule_description_no_material, rule_description_spam_caps,
    rule_tags_missing, rule_tags_too_few,
    rule_image_missing, rule_image_alt_missing,
    rule_seo_title_missing, rule_seo_desc_missing,
    rule_vendor_missing, rule_contradiction_season,
]

def analyze_product(product):
    issues = []
    for rule in RULES:
        try:
            result = rule(product)
            if result:
                code, severity, field, message, evidence = result
                issues.append({
                    "code": code,
                    "severity": severity,
                    "field": field,
                    "message": message,
                    "evidence": evidence,
                })
        except Exception as e:
            issues.append({
                "code": f"RULE_ERROR",
                "severity": "LOW",
                "field": "unknown",
                "message": f"Rule {rule.__name__} failed: {str(e)}",
                "evidence": None,
            })

    deductions = sum(SEVERITY_WEIGHTS.get(i["severity"], 0) for i in issues)
    score = max(0, 100 - deductions)
    grade = "A" if score >= 80 else "B" if score >= 60 else "C" if score >= 40 else "F"

    issue_summary = {}
    for i in issues:
        issue_summary[i["severity"]] = issue_summary.get(i["severity"], 0) + 1

    return {
        "handle": product["handle"],
        "title": product["title"],
        "score": score,
        "grade": grade,
        "totalIssues": len(issues),
        "issueSummary": issue_summary,
        "issues": issues,
    }

# ── Report builder ────────────────────────────────────────────────────────────

def build_report(products_data):
    products = products_data["products"]
    results = [analyze_product(p) for p in products]

    avg_score = sum(r["score"] for r in results) / len(results)
    store_grade = "A" if avg_score >= 80 else "B" if avg_score >= 60 else "C" if avg_score >= 40 else "F"

    all_issues = [i for r in results for i in r["issues"]]
    severity_counts = {}
    for i in all_issues:
        severity_counts[i["severity"]] = severity_counts.get(i["severity"], 0) + 1

    code_counts = {}
    for i in all_issues:
        code_counts[i["code"]] = code_counts.get(i["code"], 0) + 1
    top_issues = sorted(code_counts.items(), key=lambda x: -x[1])[:10]

    score_dist = {
        "excellent (80-100)": sum(1 for r in results if r["score"] >= 80),
        "good (60-79)":       sum(1 for r in results if 60 <= r["score"] < 80),
        "poor (40-59)":       sum(1 for r in results if 40 <= r["score"] < 60),
        "critical (<40)":     sum(1 for r in results if r["score"] < 40),
    }

    return {
        "reportMeta": {
            "generatedAt": datetime.utcnow().isoformat(),
            "store": products_data["store"],
            "productsAnalyzed": len(results),
            "rulesApplied": len(RULES),
            "avgQualityScore": round(avg_score, 1),
            "storeGrade": store_grade,
        },
        "summary": {
            "scoreDistribution": score_dist,
            "severityCounts": severity_counts,
            "topIssues": [{"code": c, "count": n} for c, n in top_issues],
        },
        "products": results,
    }

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with open("data/products.json", encoding="utf-8") as f:
        products_data = json.load(f)

    print(f"[analyzer] Analyzing {products_data['productCount']} products...")
    report = build_report(products_data)

    with open("data/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    # Print summary to terminal
    meta = report["reportMeta"]
    summary = report["summary"]
    print(f"\n{'='*50}")
    print(f"  STORE REPORT — {meta['store']}")
    print(f"{'='*50}")
    print(f"  Products analyzed : {meta['productsAnalyzed']}")
    print(f"  Avg quality score : {meta['avgQualityScore']}/100")
    print(f"  Store grade       : {meta['storeGrade']}")
    print(f"\n  Issue breakdown:")
    for sev, count in summary["severityCounts"].items():
        print(f"    {sev:<10} {count} issues")
    print(f"\n  Top problems:")
    for item in summary["topIssues"][:5]:
        print(f"    {item['code']:<35} {item['count']} products")
    print(f"{'='*50}")
    print(f"\n[analyzer] Full report saved to data/report.json")