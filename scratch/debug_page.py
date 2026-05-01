import os
import requests
from dotenv import load_dotenv

load_dotenv()

STORE = os.getenv("SHOPIFY_STORE")
TOKEN = os.getenv("SHOPIFY_TOKEN")
API_VERSION = os.getenv("SHOPIFY_API_VERSION", "2026-04")
URL = f"https://{STORE}.myshopify.com/admin/api/{API_VERSION}/graphql.json"
HEADERS = {
    "Content-Type": "application/json",
    "X-Shopify-Access-Token": TOKEN,
}

def test_page():
    query = """
    mutation CreatePage($page: PageCreateInput!) {
      pageCreate(page: $page) {
        page { id title handle }
        userErrors { field message }
      }
    }
    """
    variables = {
        "page": {
            "title": "Frequently Asked Questions (Test)",
            "body": "<h1>FAQ</h1><p>Test content.</p>"
        }
    }
    
    print(f"Attempting to create page on {STORE}...")
    res = requests.post(URL, headers=HEADERS, json={"query": query, "variables": variables})
    print(f"Status: {res.status_code}")
    print("Response JSON:")
    print(res.text)

if __name__ == "__main__":
    test_page()
