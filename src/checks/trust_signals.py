"""
src/checks/trust_signals.py
NEW FILE

Checks store and product-level trust signals that AI agents use to
assess merchant credibility before recommending them.

Trust signals AI agents look for:
  - Social proof (reviews, ratings, testimonials)
  - Guarantees (money-back, quality, authenticity)
  - Certifications (ISO, organic, BIS, ISI for India)
  - Secure payment indicators
  - Brand consistency (same vendor name across products)
  - Contact visibility
"""

import os
import re
import requests
from dotenv import load_dotenv

load_dotenv()

STORE       = os.getenv("SHOPIFY_STORE")
TOKEN       = os.getenv("SHOPIFY_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")
BASE_URL    = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}"
HEADERS     = {
    "Content-Type":           "application/json",
    "X-Shopify-Access-Token": TOKEN,
}

# ── Signal keyword sets ───────────────────────────────────────────────────────

REVIEW_KEYWORDS = [
    "review", "rating", "stars", "testimonial", "verified buyer",
    "customer review", "rated", "feedback", "trust pilot", "judge.me"
]
GUARANTEE_KEYWORDS = [
    "guarantee", "money back", "30 day", "60 day", "100%", "assured",
    "warranty", "replacement", "no questions asked", "satisfaction guaranteed"
]
CERTIFICATION_KEYWORDS = [
    "certified", "certification", "iso", "bis", "isi", "organic",
    "fssai", "halal", "agmark", "approved", "authentic", "genuine",
    "original", "licensed", "lab tested", "dermatologist tested",
    "clinically tested", "cruelty free"
]
SECURE_PAYMENT_KEYWORDS = [
    "secure payment", "ssl", "encrypted", "safe checkout", "razorpay",
    "paytm", "upi", "gpay", "cod", "cash on delivery", "emi available"
]
INDIA_TRUST_KEYWORDS = [
    "made in india", "indian brand", "gst", "pan", "msme",
    "startup india", "swadeshi", "local brand"
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").lower()


def fetch_metafields(resource: str, resource_id: str) -> list:
    try:
        r = requests.get(
            f"{BASE_URL}/{resource}/{resource_id}/metafields.json",
            headers=HEADERS, timeout=10
        )
        if r.status_code == 200:
            return r.json().get("metafields", [])
    except Exception:
        pass
    return []


def fetch_shop_info() -> dict:
    try:
        r = requests.get(f"{BASE_URL}/shop.json", headers=HEADERS, timeout=10)
        if r.status_code == 200:
            return r.json().get("shop", {})
    except Exception:
        pass
    return {}


# ── Store-level trust check ───────────────────────────────────────────────────

def check_store_trust(products: list) -> dict:
    """
    Analyses store-level trust signals using product data.
    Does not require additional API calls beyond what fetcher.py already pulls.
    """
    issues  = []
    details = {}

    # ── Brand consistency ─────────────────────────────────────────────────────
    vendors = [p.get("vendor", "").strip() for p in products if p.get("vendor", "").strip()]
    unique_vendors = set(v.lower() for v in vendors)
    missing_vendor = sum(1 for p in products if not p.get("vendor", "").strip())

    details["vendorAnalysis"] = {
        "uniqueVendors": list(unique_vendors),
        "vendorCount":   len(unique_vendors),
        "missingVendor": missing_vendor,
    }

    if missing_vendor > len(products) * 0.3:
        issues.append({
            "code":     "TRUST_VENDOR_MISSING",
            "severity": "HIGH",
            "field":    "trust",
            "message":  f"{missing_vendor}/{len(products)} products have no vendor/brand set. Brand presence is a primary AI trust signal.",
            "evidence": f"{missing_vendor} products",
        })

    if len(unique_vendors) > 5:
        issues.append({
            "code":     "TRUST_BRAND_INCONSISTENT",
            "severity": "MEDIUM",
            "field":    "trust",
            "message":  f"Store has {len(unique_vendors)} different vendor names. AI agents prefer stores with consistent brand identity.",
            "evidence": list(unique_vendors)[:5],
        })

    # ── Review / social proof signals in descriptions ─────────────────────────
    products_with_social_proof = 0
    for p in products:
        desc = strip_html(p.get("descriptionHtml", "") or p.get("descriptionPlain", ""))
        if any(kw in desc for kw in REVIEW_KEYWORDS):
            products_with_social_proof += 1

    details["socialProof"] = {
        "productsWithSocialProof": products_with_social_proof,
        "coveragePercent": round(products_with_social_proof / len(products) * 100) if products else 0,
    }

    if products_with_social_proof == 0:
        issues.append({
            "code":     "TRUST_NO_SOCIAL_PROOF",
            "severity": "HIGH",
            "field":    "trust",
            "message":  "No product descriptions mention reviews, ratings, or customer testimonials. Social proof is a top-3 AI trust signal for e-commerce.",
            "evidence": None,
        })

    # ── Guarantee signals ─────────────────────────────────────────────────────
    products_with_guarantee = 0
    for p in products:
        desc = strip_html(p.get("descriptionHtml", "") or p.get("descriptionPlain", ""))
        tags = " ".join(p.get("tags", [])).lower()
        if any(kw in desc or kw in tags for kw in GUARANTEE_KEYWORDS):
            products_with_guarantee += 1

    details["guarantees"] = {
        "productsWithGuarantee": products_with_guarantee,
    }

    if products_with_guarantee == 0:
        issues.append({
            "code":     "TRUST_NO_GUARANTEE",
            "severity": "MEDIUM",
            "field":    "trust",
            "message":  "No products mention guarantees, warranties, or money-back assurances. These directly increase AI-assisted purchase confidence.",
            "evidence": None,
        })

    # ── Certification signals ─────────────────────────────────────────────────
    products_with_cert = 0
    for p in products:
        desc = strip_html(p.get("descriptionHtml", "") or p.get("descriptionPlain", ""))
        if any(kw in desc for kw in CERTIFICATION_KEYWORDS):
            products_with_cert += 1

    details["certifications"] = {
        "productsWithCertification": products_with_cert,
    }

    # Only flag for categories where certifications matter
    skincare_electronics = [
        p for p in products
        if any(kw in (p.get("productType") or "").lower()
               for kw in ["skincare", "electronics", "food", "health"])
    ]
    if skincare_electronics and products_with_cert == 0:
        issues.append({
            "code":     "TRUST_NO_CERTIFICATION",
            "severity": "MEDIUM",
            "field":    "trust",
            "message":  "Skincare/health/electronics products have no certification mentions (dermatologist tested, BIS certified, etc). AI agents weigh these heavily for regulated categories.",
            "evidence": f"{len(skincare_electronics)} regulated-category products",
        })

    # ── Payment / India trust ─────────────────────────────────────────────────
    all_descriptions = " ".join(
        strip_html(p.get("descriptionHtml", "") or p.get("descriptionPlain", ""))
        for p in products
    )
    all_tags = " ".join(" ".join(p.get("tags", [])) for p in products).lower()
    combined = all_descriptions + " " + all_tags

    has_india_trust = any(kw in combined for kw in INDIA_TRUST_KEYWORDS)
    details["indiaTrustSignals"] = {"found": has_india_trust}

    # ── Image alt text (accessibility / AI vision trust) ─────────────────────
    total_images = sum(p.get("imageCount", 0) for p in products)
    missing_alt  = sum(p.get("imagesMissingAlt", 0) for p in products)

    details["imageAltText"] = {
        "totalImages": total_images,
        "missingAlt":  missing_alt,
        "coveragePercent": round((total_images - missing_alt) / total_images * 100) if total_images else 0,
    }

    if total_images > 0 and missing_alt / total_images > 0.5:
        issues.append({
            "code":     "TRUST_ALT_TEXT_MISSING",
            "severity": "LOW",
            "field":    "trust",
            "message":  f"{missing_alt}/{total_images} product images have no alt text. Alt text is used by vision AI agents to verify product identity.",
            "evidence": f"{missing_alt} images",
        })

    # ── Score ─────────────────────────────────────────────────────────────────
    severity_weights = {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 8, "LOW": 3}
    deductions = sum(severity_weights.get(i["severity"], 0) for i in issues)
    trust_score = max(0, 100 - deductions)

    return {
        "trustScore":  trust_score,
        "trustGrade":  "A" if trust_score >= 80 else "B" if trust_score >= 60 else "C" if trust_score >= 40 else "F",
        "totalIssues": len(issues),
        "issues":      issues,
        "details":     details,
    }


if __name__ == "__main__":
    import json
    # Test with empty products
    result = check_store_trust([])
    print(json.dumps(result, indent=2))