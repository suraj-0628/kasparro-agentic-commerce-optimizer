"""
llm_enhancer.py
Uses Google Gemini API or OpenAI API to generate improved product content.
Takes current product data + issues → returns improved title, description, tags.
"""

import os
import json
import re
import requests
import time
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = None # os.getenv("OPENAI_API_KEY")

GEMINI_ENDPOINT = (
    "https://generativelanguage.googleapis.com/v1beta/models/"
    "gemini-flash-latest:generateContent"
)


# ── Prompt builder ────────────────────────────────────────────────────────────

def build_prompt(product: dict, issues: list) -> str:
    issue_lines = "\n".join(
        f"  - [{i['severity']}] {i['field']}: {i['message']}"
        for i in issues
    )

    return f"""You are an expert Shopify product content optimizer for an Indian e-commerce store.

CURRENT PRODUCT DATA:
- Title: {product.get('title', 'N/A')}
- Description: {product.get('descriptionPlain', 'None')}
- Tags: {', '.join(product.get('tags', [])) or 'None'}
- Product Type: {product.get('productType', 'N/A')}
- Vendor: {product.get('vendor', 'N/A')}
- Price: ₹{product.get('price', 0)}

DETECTED ISSUES:
{issue_lines}

TASK:
Generate improved product content that fixes all the issues above.
The store sells everyday essentials to Indian customers.

STRICT RULES:
1. Title: 40-70 characters, clear product noun + key attribute + variant
2. Description: 80-120 words, include material/specs, use-case, target user, care instructions
3. Tags: exactly 6-8 tags, lowercase, comma separated, cover: type, material, use-case, gender, occasion
4. SEO Title: 50-60 chars, keyword-rich
5. SEO Description: 150-160 chars, benefit-focused
6. No vague phrases like "good quality" or "best product"
7. No ALL CAPS
8. Use Indian context (mention Indian occasions, sizes, usage patterns where relevant)
9. CRITICAL: Do NOT use literal newlines/line-breaks inside JSON string values. Keep all text on a single line or use \\n.

Respond ONLY with valid JSON in this exact format, no markdown, no explanation:
{{
  "title": "improved title here",
  "description": "improved description here as plain text no HTML",
  "tags": ["tag1", "tag2", "tag3", "tag4", "tag5", "tag6"],
  "seo_title": "seo title here",
  "seo_description": "seo description here",
  "changes_summary": "2-3 sentence plain English explanation of what was changed and why"
}}"""


# ── Gemini API caller ─────────────────────────────────────────────────────────

def call_gemini(prompt: str, max_retries: int = 3) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.4,
            "maxOutputTokens": 2048,
            "responseMimeType": "application/json",
        },
    }

    for attempt in range(max_retries):
        response = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            break
            
        # If it's a 503 (Unavailable) or 429 (Too Many Requests), wait and retry
        if response.status_code in (503, 429) and attempt < max_retries - 1:
            time.sleep(2 ** attempt)  # Exponential backoff: 1s, 2s
            continue

        raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

    data = response.json()
    raw_text = data["candidates"][0]["content"]["parts"][0]["text"]

    # Strip markdown fences if present
    raw_text = re.sub(r"```json|```", "", raw_text).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Gemini returned invalid JSON: {e}\nRaw: {raw_text[:300]}")


# ── OpenAI API caller ─────────────────────────────────────────────────────────

def call_openai(prompt: str, max_retries: int = 3) -> dict:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")

    payload = {
        "model": "gpt-4o-mini",
        "response_format": {"type": "json_object"},
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.4,
    }

    for attempt in range(max_retries):
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {OPENAI_API_KEY}"
            },
            json=payload,
            timeout=30,
        )

        if response.status_code == 200:
            break
            
        if response.status_code in (503, 429) and attempt < max_retries - 1:
            time.sleep(2 ** attempt)
            continue

        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]

    # Strip markdown fences if present
    raw_text = re.sub(r"```json|```", "", raw_text).strip()

    try:
        return json.loads(raw_text)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"OpenAI returned invalid JSON: {e}\nRaw: {raw_text[:300]}")


# ── Main enhancer function ────────────────────────────────────────────────────

def enhance_product(product: dict, issues: list) -> dict:
    """
    Takes a normalized product dict and its issue list.
    Returns dict with improved fields + changes summary.
    """
    prompt = build_prompt(product, issues)
    
    # Use OpenAI if key is present, otherwise fallback to Gemini
    if OPENAI_API_KEY:
        improved = call_openai(prompt)
    else:
        improved = call_gemini(prompt)

    # Wrap description in basic HTML for Shopify
    desc_html = "<p>" + improved.get("description", "").replace("\n\n", "</p><p>") + "</p>"

    return {
        "handle":          product["handle"],
        "title":           improved.get("title", product["title"]),
        "descriptionHtml": desc_html,
        "tags":            improved.get("tags", product.get("tags", [])),
        "seo": {
            "title":       improved.get("seo_title", ""),
            "description": improved.get("seo_description", ""),
        },
        "changesSummary":  improved.get("changes_summary", ""),
        "original": {
            "title":       product["title"],
            "description": product.get("descriptionPlain", ""),
            "tags":        product.get("tags", []),
        },
    }


# ── Batch enhancer ────────────────────────────────────────────────────────────

def enhance_all_products(report_path="data/report.json",
                         products_path="data/products.json",
                         output_path="data/enhanced.json"):
    with open(products_path, encoding="utf-8") as f:
        products_data = json.load(f)

    with open(report_path, encoding="utf-8") as f:
        report = json.load(f)

    products_map = {p["handle"]: p for p in products_data["products"]}
    issues_map   = {p["handle"]: p["issues"] for p in report["products"]}

    enhanced = []
    failed   = []

    for handle, product in products_map.items():
        issues = issues_map.get(handle, [])
        # Only enhance products with issues worth fixing
        high_issues = [i for i in issues if i["severity"] in ("CRITICAL", "HIGH")]
        if not high_issues:
            print(f"[enhancer] Skipping {handle} — no critical/high issues")
            continue

        print(f"[enhancer] Enhancing: {product['title']}...")
        try:
            result = enhance_product(product, issues)
            enhanced.append(result)
            print(f"  ✓ Done")
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            failed.append({"handle": handle, "error": str(e)})

    output = {
        "enhanced": enhanced,
        "failed":   failed,
        "stats": {
            "total":    len(products_map),
            "enhanced": len(enhanced),
            "skipped":  len(products_map) - len(enhanced) - len(failed),
            "failed":   len(failed),
        }
    }

    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n[enhancer] Done. {len(enhanced)} enhanced, {len(failed)} failed.")
    print(f"[enhancer] Saved to {output_path}")
    return output


if __name__ == "__main__":
    enhance_all_products()