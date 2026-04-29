"""
src/checks/faq_policy.py
NEW FILE

Checks store-level content that AI agents read beyond product data:
  - FAQ page existence and coverage
  - Return / refund policy
  - Shipping policy
  - Privacy policy
  - Contact page / support availability

AI shopping agents (Google, Perplexity, ChatGPT plugins) pull store policies
when deciding whether to recommend a merchant. Missing policies = lower trust score.
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

# ── Keyword sets for policy detection ────────────────────────────────────────

RETURN_KEYWORDS = [
    "return", "refund", "exchange", "money back", "days to return",
    "return policy", "no return", "all sales final"
]
SHIPPING_KEYWORDS = [
    "shipping", "delivery", "dispatch", "courier", "free shipping",
    "express", "standard delivery", "ships within", "processing time"
]
FAQ_KEYWORDS = [
    "faq", "frequently asked", "questions", "how do i", "how to",
    "what is", "can i", "do you", "will you"
]
CONTACT_KEYWORDS = [
    "contact", "email", "phone", "whatsapp", "support", "reach us",
    "get in touch", "help", "customer service"
]
TRUST_POLICY_KEYWORDS = [
    "privacy", "data", "gdpr", "cookie", "personal information",
    "we collect", "third party"
]


# ── Shopify data fetchers ─────────────────────────────────────────────────────

def fetch_pages() -> list:
    try:
        r = requests.get(
            f"{BASE_URL}/pages.json?limit=50&fields=id,title,body_html,handle",
            headers=HEADERS, timeout=15
        )
        if r.status_code == 200:
            return r.json().get("pages", [])
    except Exception:
        pass
    return []


def fetch_shop_policies() -> dict:
    """Fetch built-in Shopify policies (refund, shipping, privacy)."""
    try:
        r = requests.get(f"{BASE_URL}/policies.json", headers=HEADERS, timeout=15)
        if r.status_code == 200:
            return r.json().get("policies", {})
    except Exception:
        pass
    return {}


def fetch_navigation() -> list:
    """Fetch store navigation (link lists) to detect menu items."""
    try:
        r = requests.get(
            f"{BASE_URL}/custom_collections.json?limit=1",
            headers=HEADERS, timeout=10
        )
        # Just checking connectivity — nav requires storefront API
    except Exception:
        pass
    return []


# ── Text analysis helpers ─────────────────────────────────────────────────────

def strip_html(html: str) -> str:
    return re.sub(r"<[^>]+>", " ", html or "").lower()


def keyword_coverage(text: str, keywords: list) -> list:
    return [kw for kw in keywords if kw in text]


def word_count(text: str) -> int:
    return len(text.split()) if text.strip() else 0


# ── Main checker ──────────────────────────────────────────────────────────────

def check_faq_and_policies() -> dict:
    """
    Returns structured report of store-level policy and FAQ coverage.
    Issues follow same severity format as analyzer.py rules.
    """
    issues  = []
    details = {}

    pages   = fetch_pages()
    policies = fetch_shop_policies()

    page_corpus = {}
    for page in pages:
        handle = page.get("handle", "")
        text   = strip_html(page.get("body_html", "")) + " " + page.get("title", "").lower()
        page_corpus[handle] = {"text": text, "title": page.get("title", ""), "wordCount": word_count(text)}

    all_page_text = " ".join(p["text"] for p in page_corpus.values())

    # Convert policies list to a dictionary keyed by handle (e.g. 'refund-policy')
    if isinstance(policies, list):
        policies = {p.get("handle", ""): p for p in policies}

    # ── 1. Return / Refund policy ─────────────────────────────────────────────
    refund_policy = policies.get("refund-policy", {})
    has_refund_page = any(
        any(kw in p["text"] for kw in RETURN_KEYWORDS)
        for p in page_corpus.values()
    )
    has_refund_policy = bool(refund_policy.get("body"))

    if not has_refund_policy and not has_refund_page:
        issues.append({
            "code":     "POLICY_RETURN_MISSING",
            "severity": "CRITICAL",
            "field":    "store_policy",
            "message":  "No return/refund policy found. AI shopping agents flag stores without return policies as high-risk — customers are actively warned away.",
            "evidence": None,
        })
    elif has_refund_policy:
        body = strip_html(refund_policy.get("body", ""))
        wc   = word_count(body)
        if wc < 50:
            issues.append({
                "code":     "POLICY_RETURN_TOO_SHORT",
                "severity": "HIGH",
                "field":    "store_policy",
                "message":  f"Return policy exists but is very thin ({wc} words). AI agents need clear terms: timeframe, conditions, process.",
                "evidence": f"{wc} words",
            })
        details["returnPolicy"] = {"wordCount": wc, "found": True}
    else:
        details["returnPolicy"] = {"wordCount": 0, "found": True, "source": "page"}

    # ── 2. Shipping policy ────────────────────────────────────────────────────
    shipping_policy = policies.get("shipping-policy", {})
    has_shipping_policy = bool(shipping_policy.get("body"))
    has_shipping_page   = any(
        any(kw in p["text"] for kw in SHIPPING_KEYWORDS)
        for p in page_corpus.values()
    )

    if not has_shipping_policy and not has_shipping_page:
        issues.append({
            "code":     "POLICY_SHIPPING_MISSING",
            "severity": "HIGH",
            "field":    "store_policy",
            "message":  "No shipping policy found. AI agents answering 'when will my order arrive?' cannot answer for this store — reducing recommendation likelihood.",
            "evidence": None,
        })
    else:
        if has_shipping_policy:
            body = strip_html(shipping_policy.get("body", ""))
            wc   = word_count(body)
            # Check for specific shipping time mention
            has_time = bool(re.search(r'\b\d+[\s-]*(day|business day|week|hour)', body))
            if not has_time:
                issues.append({
                    "code":     "POLICY_SHIPPING_NO_TIMEFRAME",
                    "severity": "MEDIUM",
                    "field":    "store_policy",
                    "message":  "Shipping policy exists but mentions no specific delivery timeframe. AI agents cannot answer 'how long does shipping take?'",
                    "evidence": None,
                })
            details["shippingPolicy"] = {"wordCount": wc, "hasTimeframe": has_time, "found": True}

    # ── 3. Privacy policy ─────────────────────────────────────────────────────
    privacy_policy = policies.get("privacy-policy", {})
    has_privacy = bool(privacy_policy.get("body"))

    if not has_privacy:
        has_privacy_page = any(
            any(kw in p["text"] for kw in TRUST_POLICY_KEYWORDS)
            for p in page_corpus.values()
        )
        if not has_privacy_page:
            issues.append({
                "code":     "POLICY_PRIVACY_MISSING",
                "severity": "MEDIUM",
                "field":    "store_policy",
                "message":  "No privacy policy found. Required for trust signals and reduces AI agent recommendation confidence.",
                "evidence": None,
            })

    # ── 4. FAQ page ───────────────────────────────────────────────────────────
    faq_pages = [
        p for handle, p in page_corpus.items()
        if "faq" in handle or "frequently" in p["title"].lower()
        or len(keyword_coverage(p["text"], FAQ_KEYWORDS)) >= 3
    ]

    if not faq_pages:
        issues.append({
            "code":     "FAQ_MISSING",
            "severity": "HIGH",
            "field":    "store_faq",
            "message":  "No FAQ page found. AI agents use FAQ content to answer pre-purchase questions. Without it, the store loses 'answer box' placement in AI search results.",
            "evidence": None,
        })
    else:
        faq_text = " ".join(p["text"] for p in faq_pages)
        faq_wc   = word_count(faq_text)
        if faq_wc < 200:
            issues.append({
                "code":     "FAQ_TOO_SHORT",
                "severity": "MEDIUM",
                "field":    "store_faq",
                "message":  f"FAQ page exists but is very thin ({faq_wc} words). AI agents need substantive Q&A content to extract answers.",
                "evidence": f"{faq_wc} words",
            })
        # Check for key topic coverage
        missing_topics = []
        if not any(kw in faq_text for kw in RETURN_KEYWORDS):
            missing_topics.append("returns/refunds")
        if not any(kw in faq_text for kw in SHIPPING_KEYWORDS):
            missing_topics.append("shipping")
        if not any(kw in faq_text for kw in CONTACT_KEYWORDS):
            missing_topics.append("contact/support")
        if missing_topics:
            issues.append({
                "code":     "FAQ_MISSING_TOPICS",
                "severity": "MEDIUM",
                "field":    "store_faq",
                "message":  f"FAQ page is missing coverage for: {', '.join(missing_topics)}. These are the most common AI-answered pre-purchase questions.",
                "evidence": missing_topics,
            })
        details["faq"] = {"wordCount": faq_wc, "found": True, "pageCount": len(faq_pages)}

    # ── 5. Contact / Support ──────────────────────────────────────────────────
    has_contact = any(
        any(kw in p["text"] for kw in CONTACT_KEYWORDS)
        for p in page_corpus.values()
    ) or any(kw in all_page_text for kw in ["@", "support@", "contact@"])

    if not has_contact:
        issues.append({
            "code":     "CONTACT_MISSING",
            "severity": "MEDIUM",
            "field":    "store_policy",
            "message":  "No contact/support information found in store pages. AI agents rank stores with visible support channels higher for trust.",
            "evidence": None,
        })

    # ── Score ─────────────────────────────────────────────────────────────────
    severity_weights = {"CRITICAL": 30, "HIGH": 15, "MEDIUM": 8, "LOW": 3}
    deductions = sum(severity_weights.get(i["severity"], 0) for i in issues)
    policy_score = max(0, 100 - deductions)

    return {
        "policyScore":  policy_score,
        "policyGrade":  "A" if policy_score >= 80 else "B" if policy_score >= 60 else "C" if policy_score >= 40 else "F",
        "totalIssues":  len(issues),
        "issues":       issues,
        "details":      details,
        "pagesChecked": len(pages),
    }


if __name__ == "__main__":
    import json
    result = check_faq_and_policies()
    print(json.dumps(result, indent=2))