"""
src/fetcher.py
REPLACE EXISTING

Fixes:
  - Category bug: falls back to productType when taxonomy category is null
  - Retry logic with exponential backoff (3 attempts)
  - Graceful timeout handling
  - API version from .env
  - Pagination support for stores with > 30 products
"""

import os
import re
import json
import time
import requests
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

STORE       = os.getenv("SHOPIFY_STORE")
TOKEN       = os.getenv("SHOPIFY_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")
ENDPOINT    = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "Content-Type":           "application/json",
    "X-Shopify-Access-Token": TOKEN,
}

QUERY = """
query FetchProducts($first: Int!, $after: String) {
  products(first: $first, after: $after) {
    pageInfo {
      hasNextPage
      endCursor
    }
    edges {
      node {
        id
        handle
        title
        descriptionHtml
        productType
        vendor
        status
        tags
        createdAt
        updatedAt
        priceRangeV2 {
          minVariantPrice { amount currencyCode }
        }
        images(first: 5) {
          edges { node { url altText } }
        }
        variants(first: 5) {
          edges {
            node { id sku price inventoryQuantity }
          }
        }
        seo { title description }
        category { name fullName }
      }
    }
  }
}
"""


# ── Retry wrapper ─────────────────────────────────────────────────────────────

def graphql_request(variables: dict, max_retries: int = 3) -> dict:
    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                ENDPOINT,
                headers=HEADERS,
                json={"query": QUERY, "variables": variables},
                timeout=20,
            )
            if response.status_code == 429:
                wait = 2 ** attempt
                print(f"  [fetcher] Rate limited — waiting {wait}s...")
                time.sleep(wait)
                continue
            if response.status_code != 200:
                raise RuntimeError(f"HTTP {response.status_code}: {response.text[:200]}")
            data = response.json()
            if "errors" in data:
                raise RuntimeError(f"GraphQL errors: {data['errors']}")
            return data["data"]
        except requests.exceptions.Timeout:
            last_error = "Request timed out"
            time.sleep(2 ** attempt)
        except requests.exceptions.ConnectionError:
            last_error = "Connection failed"
            time.sleep(2 ** attempt)
        except Exception as e:
            last_error = str(e)
            if attempt == max_retries - 1:
                break
            time.sleep(2 ** attempt)
    raise RuntimeError(f"Fetcher failed after {max_retries} attempts: {last_error}")


# ── Normalizer ────────────────────────────────────────────────────────────────

def normalize_product(node: dict) -> dict:
    desc_plain = re.sub(r"<[^>]+>", " ", node.get("descriptionHtml") or "")
    desc_plain = re.sub(r"\s+", " ", desc_plain).strip()

    images = [
        {"url": e["node"]["url"], "altText": e["node"].get("altText")}
        for e in node.get("images", {}).get("edges", [])
    ]

    variants = [
        {
            "id":        e["node"]["id"],
            "sku":       e["node"].get("sku") or "",
            "price":     float(e["node"]["price"]),
            "inventory": e["node"].get("inventoryQuantity"),
        }
        for e in node.get("variants", {}).get("edges", [])
    ]

    # ── Category fix ──────────────────────────────────────────────────────────
    # Shopify taxonomy category is only set when using new standard taxonomy.
    # Most stores (and CSV imports) use productType instead.
    # We unify both into a single "category" field so analyzer rules work correctly.
    raw_category = node.get("category")
    product_type = (node.get("productType") or "").strip()

    if raw_category and raw_category.get("name"):
        category = {
            "name":     raw_category["name"],
            "fullName": raw_category.get("fullName", raw_category["name"]),
            "source":   "taxonomy",
        }
    elif product_type:
        category = {
            "name":     product_type,
            "fullName": product_type,
            "source":   "productType",  # flagged so UI can show "upgrade to taxonomy" hint
        }
    else:
        category = None

    price_range = node.get("priceRangeV2", {}).get("minVariantPrice", {})

    return {
        "id":                   node["id"],
        "handle":               node["handle"],
        "title":                node.get("title", "").strip(),
        "descriptionHtml":      node.get("descriptionHtml") or "",
        "descriptionPlain":     desc_plain,
        "descriptionWordCount": len(desc_plain.split()) if desc_plain else 0,
        "productType":          product_type,
        "vendor":               (node.get("vendor") or "").strip(),
        "status":               node.get("status"),
        "tags":                 node.get("tags") or [],
        "category":             category,
        "price":                float(price_range.get("amount", 0)),
        "currency":             price_range.get("currencyCode", "INR"),
        "images":               images,
        "imageCount":           len(images),
        "hasImages":            len(images) > 0,
        "imagesMissingAlt":     sum(1 for i in images if not i.get("altText")),
        "variants":             variants,
        "variantCount":         len(variants),
        "seo":                  node.get("seo") or {},
        "createdAt":            node.get("createdAt"),
        "updatedAt":            node.get("updatedAt"),
    }


# ── Paginated fetch ───────────────────────────────────────────────────────────

def fetch_products(max_products: int = 250) -> dict:
    if not STORE or not TOKEN:
        raise ValueError("SHOPIFY_STORE and SHOPIFY_TOKEN must be set in .env")

    print(f"[fetcher] Connecting to {STORE}.myshopify.com (API {API_VERSION})...")

    products = []
    cursor   = None
    page     = 1

    while len(products) < max_products:
        batch = min(50, max_products - len(products))
        print(f"  [fetcher] Page {page} (batch {batch})...")

        variables = {"first": batch, "after": cursor}
        data      = graphql_request(variables)
        edges     = data["products"]["edges"]
        page_info = data["products"]["pageInfo"]

        for edge in edges:
            products.append(normalize_product(edge["node"]))

        if not page_info["hasNextPage"] or not edges:
            break
        cursor = page_info["endCursor"]
        page  += 1

    print(f"[fetcher] Fetched {len(products)} products.")

    # Count how many used taxonomy vs productType fallback
    taxonomy_count  = sum(1 for p in products if p.get("category", {}) and p["category"].get("source") == "taxonomy")
    fallback_count  = sum(1 for p in products if p.get("category", {}) and p["category"].get("source") == "productType")
    no_cat_count    = sum(1 for p in products if not p.get("category"))

    output = {
        "store":        STORE,
        "fetchedAt":    __import__("datetime").datetime.now().isoformat(),
        "apiVersion":   API_VERSION,
        "productCount": len(products),
        "categoryStats": {
            "usingTaxonomy":   taxonomy_count,
            "usingProductType": fallback_count,
            "noCategory":      no_cat_count,
        },
        "products": products,
    }

    Path("data").mkdir(exist_ok=True)
    with open("data/products.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"[fetcher] Saved to data/products.json")
    print(f"  Category sources: taxonomy={taxonomy_count}, productType={fallback_count}, none={no_cat_count}")
    return output


if __name__ == "__main__":
    fetch_products()