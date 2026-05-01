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

def test_policy():
    query = """
    mutation shopPolicyUpdate($shopPolicy: ShopPolicyInput!) {
      shopPolicyUpdate(shopPolicy: $shopPolicy) {
        shopPolicy { title body }
        userErrors { field message }
      }
    }
    """
    # Attempting to update REFUND_POLICY
    variables = {
        "shopPolicy": {
            "type": "REFUND_POLICY",
            "body": "<h1>Refund Policy</h1><p>Test policy created by AI Optimizer.</p>"
        }
    }
    
    print(f"Connecting to {STORE}...")
    res = requests.post(URL, headers=HEADERS, json={"query": query, "variables": variables})
    print(f"Status: {res.status_code}")
    print("Response JSON:")
    print(res.text)

if __name__ == "__main__":
    test_policy()
