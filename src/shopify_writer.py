"""
shopify_writer.py
Pushes approved text changes back to Shopify via Admin REST API.
Requires write_products scope on the access token.
"""

import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

STORE       = os.getenv("SHOPIFY_STORE")
TOKEN       = os.getenv("SHOPIFY_TOKEN")
API_VERSION = "2026-04"

BASE_URL = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}"
HEADERS  = {
    "Content-Type":           "application/json",
    "X-Shopify-Access-Token": TOKEN,
}


# ── Core updater ──────────────────────────────────────────────────────────────

def update_product(product_id: str, updates: dict) -> dict:
    """
    Updates a Shopify product with the given fields.
    product_id: numeric ID or gid://shopify/Product/XXXXX
    updates: dict of fields to update — title, body_html, tags, etc.

    Returns { success, data/error }
    """
    numeric_id = product_id.split("/")[-1] if "/" in product_id else product_id
    endpoint   = f"{BASE_URL}/products/{numeric_id}.json"

    payload = {"product": updates}

    response = requests.put(
        endpoint,
        headers=HEADERS,
        json=payload,
        timeout=30,
    )

    if response.status_code == 200:
        return {
            "success":   True,
            "productId": numeric_id,
            "updated":   list(updates.keys()),
            "data":      response.json().get("product", {}),
        }
    else:
        return {
            "success":   False,
            "productId": numeric_id,
            "error":     f"HTTP {response.status_code}: {response.text[:300]}",
        }


# ── SEO updater (uses metafields endpoint) ────────────────────────────────────

def update_seo(product_id: str, seo_title: str, seo_description: str) -> dict:
    """
    Updates SEO title and description via metafields.
    Shopify stores SEO data as global.title_tag and global.description_tag metafields.
    """
    numeric_id = product_id.split("/")[-1] if "/" in product_id else product_id
    endpoint   = f"{BASE_URL}/products/{numeric_id}/metafields.json"

    results = []
    for key, value in [("title_tag", seo_title), ("description_tag", seo_description)]:
        if not value:
            continue
        payload = {
            "metafield": {
                "namespace": "global",
                "key":       key,
                "value":     value,
                "type":      "single_line_text_field",
            }
        }
        resp = requests.post(endpoint, headers=HEADERS, json=payload, timeout=30)
        results.append({
            "key":     key,
            "success": resp.status_code in (200, 201),
            "status":  resp.status_code,
        })

    all_ok = all(r["success"] for r in results)
    return {
        "success": all_ok,
        "results": results,
    }


# ── High-level apply function ─────────────────────────────────────────────────

def apply_enhanced_content(product_id: str, enhanced: dict) -> dict:
    """
    Takes the output from llm_enhancer.enhance_product() and applies it.
    Handles: title, description, tags, SEO.

    Returns structured result with per-field status.
    """
    field_results = {}

    # Build core product update payload
    core_updates = {}
    if enhanced.get("title"):
        core_updates["title"] = enhanced["title"]
    if enhanced.get("descriptionHtml"):
        core_updates["body_html"] = enhanced["descriptionHtml"]
    if enhanced.get("tags"):
        tags = enhanced["tags"]
        core_updates["tags"] = ", ".join(tags) if isinstance(tags, list) else tags

    # Apply core fields
    if core_updates:
        result = update_product(product_id, core_updates)
        field_results["core"] = {
            "success": result["success"],
            "fields":  list(core_updates.keys()),
            "error":   result.get("error"),
        }
    else:
        field_results["core"] = {"success": True, "fields": [], "note": "No core fields to update"}

    # Apply SEO
    seo = enhanced.get("seo", {})
    if seo.get("title") or seo.get("description"):
        seo_result = update_seo(product_id, seo.get("title", ""), seo.get("description", ""))
        field_results["seo"] = seo_result
    else:
        field_results["seo"] = {"success": True, "note": "No SEO fields provided"}

    all_ok = all(v.get("success", False) for v in field_results.values())

    return {
        "success":       all_ok,
        "productId":     product_id,
        "handle":        enhanced.get("handle", ""),
        "fieldResults":  field_results,
        "changesSummary": enhanced.get("changesSummary", ""),
    }


# ── Batch apply ───────────────────────────────────────────────────────────────

def apply_all_enhanced(enhanced_path="data/enhanced.json",
                       products_path="data/products.json") -> dict:
    """
    Reads enhanced.json and applies all changes to Shopify.
    Maps handles back to product IDs using products.json.
    """
    with open(enhanced_path, encoding="utf-8") as f:
        enhanced_data = json.load(f)

    with open(products_path, encoding="utf-8") as f:
        products_data = json.load(f)

    id_map = {p["handle"]: p["id"] for p in products_data["products"]}

    results    = []
    successful = 0
    failed     = 0

    for item in enhanced_data.get("enhanced", []):
        handle     = item["handle"]
        product_id = id_map.get(handle)

        if not product_id:
            print(f"[writer] ✗ Cannot find ID for handle: {handle}")
            failed += 1
            continue

        print(f"[writer] Applying changes to: {item.get('title', handle)}...")
        result = apply_enhanced_content(product_id, item)

        if result["success"]:
            print(f"  ✓ Applied successfully")
            successful += 1
        else:
            print(f"  ✗ Failed: {result['fieldResults']}")
            failed += 1

        results.append(result)

    summary = {
        "total":      len(enhanced_data.get("enhanced", [])),
        "successful": successful,
        "failed":     failed,
        "results":    results,
    }

    with open("data/write_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n[writer] Done. {successful} applied, {failed} failed.")
    print(f"[writer] Results saved to data/write_results.json")
    return summary


if __name__ == "__main__":
    apply_all_enhanced()