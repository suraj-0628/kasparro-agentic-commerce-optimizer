import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()

STORE = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("SHOPIFY_TOKEN")
API_VERSION = "2026-04"
ENDPOINT = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/graphql.json"

HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": TOKEN,
}

QUERY = """
{
  products(first: 30) {
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
        priceRangeV2 {
          minVariantPrice {
            amount
            currencyCode
          }
        }
        images(first: 3) {
          edges {
            node {
              url
              altText
            }
          }
        }
        variants(first: 5) {
          edges {
            node {
              sku
              price
            }
          }
        }
        seo {
          title
          description
        }
      }
    }
  }
}
"""

def fetch_products():
    print(f"[fetcher] Connecting to {STORE}.myshopify.com...")
    
    response = requests.post(
        ENDPOINT,
        headers=HEADERS,
        json={"query": QUERY}
    )
    
    if response.status_code != 200:
        print(f"[ERROR] HTTP {response.status_code}: {response.text}")
        return
    
    data = response.json()
    
    if "errors" in data:
        print(f"[ERROR] GraphQL: {data['errors']}")
        return
    
    products = []
    for edge in data["data"]["products"]["edges"]:
        node = edge["node"]
        
        # Strip HTML from description
        import re
        desc_plain = re.sub(r'<[^>]+>', ' ', node.get("descriptionHtml") or "")
        desc_plain = re.sub(r'\s+', ' ', desc_plain).strip()
        
        images = [
            {"url": e["node"]["url"], "altText": e["node"]["altText"]}
            for e in node["images"]["edges"]
        ]
        
        products.append({
            "id": node["id"],
            "handle": node["handle"],
            "title": node["title"],
            "descriptionPlain": desc_plain,
            "descriptionWordCount": len(desc_plain.split()) if desc_plain else 0,
            "productType": node.get("productType"),
            "vendor": node.get("vendor"),
            "status": node.get("status"),
            "tags": node.get("tags", []),
            "price": float(node["priceRangeV2"]["minVariantPrice"]["amount"]),
            "currency": node["priceRangeV2"]["minVariantPrice"]["currencyCode"],
            "images": images,
            "imageCount": len(images),
            "hasImages": len(images) > 0,
            "imagesMissingAlt": sum(1 for i in images if not i["altText"]),
            "seo": node.get("seo", {}),
        })
    
    print(f"[fetcher] Fetched {len(products)} products.")
    
    output = {
        "store": STORE,
        "productCount": len(products),
        "products": products
    }
    
    # Save to data/products.json
    os.makedirs("data", exist_ok=True)
    with open("data/products.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    print("[fetcher] Saved to data/products.json")
    return output

if __name__ == "__main__":
    fetch_products()