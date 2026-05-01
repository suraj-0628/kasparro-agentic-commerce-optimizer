"""
src/shopify_writer.py
REPLACE EXISTING

Fixes:
  - SEO metafield: checks if metafield exists first → uses PUT, not POST (was silently failing on re-runs)
  - Saves changelog to data/changelog.json before every write (enables undo)
  - API version from .env
  - Better error messages with field-level detail
"""

import os
import json
import requests
from datetime import datetime, timezone
from pathlib import Path
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

# ── GraphQL Helper ────────────────────────────────────────────────────────────

def run_graphql(query: str, variables: dict = None) -> dict:
    url = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
    payload = {"query": query, "variables": variables or {}}
    try:
        r = requests.post(url, headers=HEADERS, json=payload, timeout=30)
        return r.json()
    except Exception as e:
        return {"errors": [{"message": str(e)}]}


# ── Changelog ─────────────────────────────────────────────────────────────────

def record_changelog(handle: str, product_id: str, before: dict, after: dict):
    """
    Saves a before/after record to data/changelog.json.
    This is the undo history — allows merchants to revert changes.
    """
    changelog_path = Path("data/changelog.json")
    try:
        if changelog_path.exists():
            with open(changelog_path, encoding="utf-8") as f:
                changelog = json.load(f)
        else:
            changelog = []

        changelog.append({
            "timestamp":  datetime.now(timezone.utc).isoformat(),
            "handle":     handle,
            "productId":  product_id,
            "before":     before,
            "after":      after,
        })

        with open(changelog_path, "w", encoding="utf-8") as f:
            json.dump(changelog, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"  [writer] Warning: could not save changelog: {e}")


# ── Product updater ───────────────────────────────────────────────────────────

def update_product(product_id: str, updates: dict) -> dict:
    numeric_id = product_id.split("/")[-1] if "/" in product_id else product_id
    response   = requests.put(
        f"{BASE_URL}/products/{numeric_id}.json",
        headers=HEADERS,
        json={"product": updates},
        timeout=30,
    )
    if response.status_code == 200:
        return {"success": True, "productId": numeric_id, "updated": list(updates.keys())}
    return {
        "success":   False,
        "productId": numeric_id,
        "error":     f"HTTP {response.status_code}: {response.text[:200]}",
    }


# ── SEO metafield updater (POST or PUT correctly) ─────────────────────────────

def get_existing_metafields(product_id: str) -> dict:
    """Returns {key: metafield_id} for existing global metafields on this product."""
    numeric_id = product_id.split("/")[-1] if "/" in product_id else product_id
    try:
        r = requests.get(
            f"{BASE_URL}/products/{numeric_id}/metafields.json?namespace=global",
            headers=HEADERS, timeout=15,
        )
        if r.status_code == 200:
            return {
                mf["key"]: mf["id"]
                for mf in r.json().get("metafields", [])
                if mf.get("namespace") == "global"
            }
    except Exception:
        pass
    return {}


def update_seo(product_id: str, seo_title: str, seo_description: str) -> dict:
    """
    Correctly handles POST (create) vs PUT (update) for SEO metafields.
    Previous version always POSTed — caused silent failures on re-runs.
    """
    numeric_id       = product_id.split("/")[-1] if "/" in product_id else product_id
    existing         = get_existing_metafields(product_id)
    results          = []

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

        existing_id = existing.get(key)

        if existing_id:
            # UPDATE — use PUT
            resp = requests.put(
                f"{BASE_URL}/metafields/{existing_id}.json",
                headers=HEADERS,
                json=payload,
                timeout=15,
            )
        else:
            # CREATE — use POST
            resp = requests.post(
                f"{BASE_URL}/products/{numeric_id}/metafields.json",
                headers=HEADERS,
                json=payload,
                timeout=15,
            )

        results.append({
            "key":      key,
            "action":   "update" if existing_id else "create",
            "success":  resp.status_code in (200, 201),
            "status":   resp.status_code,
        })

    return {
        "success": all(r["success"] for r in results) if results else True,
        "results": results,
    }


# ── Apply enhanced content ────────────────────────────────────────────────────

def apply_enhanced_content(product_id: str, enhanced: dict) -> dict:
    field_results = {}

    # Save changelog BEFORE writing
    record_changelog(
        handle=enhanced.get("handle", ""),
        product_id=product_id,
        before=enhanced.get("original", {}),
        after={
            "title":       enhanced.get("title"),
            "description": enhanced.get("descriptionPlain", ""),
            "tags":        enhanced.get("tags", []),
            "seo":         enhanced.get("seo", {}),
        },
    )

    # Core product fields
    core_updates = {}
    if enhanced.get("title"):
        core_updates["title"] = enhanced["title"]
    if enhanced.get("descriptionHtml"):
        core_updates["body_html"] = enhanced["descriptionHtml"]
    if enhanced.get("tags"):
        tags = enhanced["tags"]
        core_updates["tags"] = ", ".join(tags) if isinstance(tags, list) else tags
    if enhanced.get("product_type"):
        core_updates["product_type"] = enhanced["product_type"]

    if core_updates:
        result = update_product(product_id, core_updates)
        field_results["core"] = {
            "success": result["success"],
            "fields":  list(core_updates.keys()),
            "error":   result.get("error"),
        }
    else:
        field_results["core"] = {"success": True, "fields": [], "note": "Nothing to update"}

    # SEO fields
    seo = enhanced.get("seo", {})
    if seo.get("title") or seo.get("description"):
        field_results["seo"] = update_seo(
            product_id,
            seo.get("title", ""),
            seo.get("description", ""),
        )
    else:
        field_results["seo"] = {"success": True, "note": "No SEO data provided"}
    
    # Variants / SKUs
    for v in enhanced.get("variants", []):
        if v.get("id") and v.get("sku"):
            update_variant_sku(v["id"], v["sku"])

    return {
        "success":        all(v.get("success", False) for v in field_results.values()),
        "productId":      product_id,
        "handle":         enhanced.get("handle", ""),
        "fieldResults":   field_results,
        "changesSummary": enhanced.get("changesSummary", ""),
        "appliedAt":      datetime.now(timezone.utc).isoformat(),
    }


# ── Undo last change ──────────────────────────────────────────────────────────

def undo_last_change(handle: str, products_path: str = "data/products.json") -> dict:
    """
    Reverts the most recent change for a product handle using changelog.json.
    """
    changelog_path = Path("data/changelog.json")
    if not changelog_path.exists():
        return {"success": False, "error": "No changelog found"}

    with open(changelog_path, encoding="utf-8") as f:
        changelog = json.load(f)

    # Find most recent entry for this handle
    entries = [e for e in changelog if e["handle"] == handle]
    if not entries:
        return {"success": False, "error": f"No changelog entry for {handle}"}

    last = entries[-1]
    before = last["before"]

    # Load product ID
    with open(products_path, encoding="utf-8") as f:
        products_data = json.load(f)
    product = next((p for p in products_data["products"] if p["handle"] == handle), None)
    if not product:
        return {"success": False, "error": "Product not found in products.json"}

    # Revert
    revert_payload = {}
    if before.get("title"):       revert_payload["title"]    = before["title"]
    if before.get("description"): revert_payload["body_html"] = f"<p>{before['description']}</p>"
    if before.get("tags"):
        tags = before["tags"]
        revert_payload["tags"] = ", ".join(tags) if isinstance(tags, list) else tags

    result = update_product(product["id"], revert_payload)
    return {
        "success":   result["success"],
        "handle":    handle,
        "revertedTo": before,
        "error":     result.get("error"),
    }


# ── Batch apply ───────────────────────────────────────────────────────────────

def apply_all_enhanced(
    enhanced_path = "data/enhanced.json",
    products_path = "data/products.json",
) -> dict:
    with open(enhanced_path, encoding="utf-8") as f:
        enhanced_data = json.load(f)
    with open(products_path, encoding="utf-8") as f:
        products_data = json.load(f)

    id_map     = {p["handle"]: p["id"] for p in products_data["products"]}
    results    = []
    successful = 0
    failed     = 0

    for item in enhanced_data.get("enhanced", []):
        handle     = item["handle"]
        product_id = id_map.get(handle)
        if not product_id:
            print(f"  [writer] ✗ ID not found for: {handle}")
            failed += 1
            continue

        print(f"  [writer] Applying: {item.get('title', handle)[:50]}...")
        result = apply_enhanced_content(product_id, item)
        if result["success"]:
            print(f"    ✓ Applied")
            successful += 1
        else:
            print(f"    ✗ Failed: {result['fieldResults']}")
            failed += 1
        results.append(result)

    summary = {
        "appliedAt":  datetime.now(timezone.utc).isoformat(),
        "total":      len(enhanced_data.get("enhanced", [])),
        "successful": successful,
        "failed":     failed,
        "results":    results,
    }

    with open("data/write_results.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    print(f"\n[writer] Done. applied={successful} failed={failed}")
    return summary


# ── Advanced Global Fixers ────────────────────────────────────────────────────

def update_variant_sku(variant_id: str, sku: str) -> dict:
    """Updates a product variant SKU via GraphQL."""
    query = """
    mutation variantUpdate($input: ProductVariantInput!) {
      productVariantUpdate(input: $input) {
        productVariant { id sku }
        userErrors { field message }
      }
    }
    """
    # Sanitize GID: ensure it's not double-prefixed or malformed
    v_id = variant_id
    if not v_id.startswith("gid://"):
        v_id = f"gid://shopify/ProductVariant/{v_id}"
    elif v_id.count("gid://") > 1:
        # Handle cases where we accidentally double-prefixed
        v_id = "gid://" + v_id.split("gid://")[-1]
    
    variables = {"input": {"id": v_id, "sku": sku}}
    res = run_graphql(query, variables)
    
    if "errors" in res:
        return {"success": False, "error": res["errors"][0]["message"]}
    
    data = res.get("data", {}).get("productVariantUpdate", {})
    if data.get("userErrors"):
        return {"success": False, "error": data["userErrors"][0]["message"]}
    
    return {"success": True, "variantId": v_id, "newSku": sku}


def update_shop_policy(policy_type: str, body: str) -> dict:
    """
    Updates a legal policy (e.g. REFUND_POLICY, PRIVACY_POLICY, SHIPPING_POLICY).
    Requires 'write_legal_policies' scope.
    """
    query = """
    mutation shopPolicyUpdate($shopPolicy: ShopPolicyInput!) {
      shopPolicyUpdate(shopPolicy: $shopPolicy) {
        shopPolicy { body title }
        userErrors { field message }
      }
    }
    """
    # Policy types in GQL: REFUND_POLICY, PRIVACY_POLICY, SHIPPING_POLICY, TERMS_OF_SERVICE
    variables = {"shopPolicy": {"type": policy_type, "body": body}}
    res = run_graphql(query, variables)
    
    if "errors" in res:
        return {"success": False, "error": res["errors"][0]["message"]}
    
    data = res.get("data", {}).get("shopPolicyUpdate", {})
    if data.get("userErrors"):
        return {"success": False, "error": data["userErrors"][0]["message"]}
    
    return {"success": True, "policyType": policy_type}


def create_page(title: str, body_html: str) -> dict:
    """Creates a new Online Store page (e.g. 'About Us')."""
    query = """
    mutation pageCreate($page: PageCreateInput!) {
      pageCreate(page: $page) {
        page { id title handle }
        userErrors { field message }
      }
    }
    """
    variables = {"page": {"title": title, "body": body_html}}
    res = run_graphql(query, variables)
    
    if "errors" in res:
        return {"success": False, "error": res["errors"][0]["message"]}
    
    data = res.get("data", {}).get("pageCreate", {})
    if data.get("userErrors"):
        return {"success": False, "error": data["userErrors"][0]["message"]}
    
    return {"success": True, "pageId": data["page"]["id"], "handle": data["page"]["handle"]}


if __name__ == "__main__":
    apply_all_enhanced()