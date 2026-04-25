"""
main.py
Runs the full AI Representation Optimizer pipeline in one command.

Usage:
    python main.py              # fetch + analyze + perceive + recommend
    python main.py --enhance    # also run LLM enhancement (uses Gemini API)
    python main.py --apply      # also push changes to Shopify
    python main.py --serve      # run pipeline then launch dashboard
    python main.py --full       # everything: pipeline + enhance + apply + serve
"""

import sys
import os

# Add project root to sys.path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Ensure stdout uses utf-8 for box drawing characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

import json
import time
import argparse
import subprocess
from datetime import datetime

# ── Argument parser ───────────────────────────────────────────────────────────

parser = argparse.ArgumentParser(description="AI Representation Optimizer")
parser.add_argument("--enhance", action="store_true", help="Run LLM enhancement via Gemini")
parser.add_argument("--apply",   action="store_true", help="Push enhanced content to Shopify")
parser.add_argument("--serve",   action="store_true", help="Launch web dashboard after pipeline")
parser.add_argument("--full",    action="store_true", help="Run everything")
args = parser.parse_args()

if args.full:
    args.enhance = True
    args.apply   = True
    args.serve   = True

# ── Helpers ───────────────────────────────────────────────────────────────────

def section(title: str):
    print(f"\n{'─'*55}")
    print(f"  {title}")
    print(f"{'─'*55}")

def step(msg: str):
    print(f"\n  → {msg}")

def ok(msg: str):
    print(f"  ✓ {msg}")

def fail(msg: str):
    print(f"  ✗ {msg}")

def load_json(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)

# ── Pipeline steps ────────────────────────────────────────────────────────────

def run_fetcher():
    section("STEP 1 — Fetching products from Shopify")
    step("Connecting to Shopify Admin GraphQL API...")
    from src.fetcher import fetch_products
    result = fetch_products()
    if result:
        ok(f"Fetched {result['productCount']} products → data/products.json")
        return True
    else:
        fail("Fetcher failed. Check your SHOPIFY_STORE and SHOPIFY_TOKEN in .env")
        return False


def run_analyzer():
    section("STEP 2 — Analyzing product quality")
    step("Running 17 quality rules...")
    from src.analyzer import build_report
    products_data = load_json("data/products.json")
    report = build_report(products_data)

    with open("data/report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    meta    = report["reportMeta"]
    summary = report["summary"]
    ok(f"Store score: {meta['avgQualityScore']}/100 (Grade {meta['storeGrade']})")
    ok(f"Issues found — CRITICAL: {summary['severityCounts'].get('CRITICAL',0)} | "
       f"HIGH: {summary['severityCounts'].get('HIGH',0)} | "
       f"MEDIUM: {summary['severityCounts'].get('MEDIUM',0)} | "
       f"LOW: {summary['severityCounts'].get('LOW',0)}")
    ok("Saved → data/report.json")
    return True


def run_perception():
    section("STEP 3 — Simulating AI perception")
    step("Classifying products as an AI agent would...")
    from src.ai_perception import generate_perception
    products_data = load_json("data/products.json")
    perceptions   = [generate_perception(p) for p in products_data["products"]]

    avg_retrieval = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / len(perceptions)
    ambiguous     = sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"])

    type_dist = {}
    for p in perceptions:
        t = p["aiPerception"]["perceivedType"]
        type_dist[t] = type_dist.get(t, 0) + 1

    output = {
        "meta": {
            "generatedAt":       datetime.now().isoformat(),
            "productsProcessed": len(perceptions),
            "avgRetrievalScore": round(avg_retrieval, 1),
            "storeVisibility":   (
                "HIGH"     if avg_retrieval >= 75 else
                "MEDIUM"   if avg_retrieval >= 50 else
                "LOW"      if avg_retrieval >= 25 else
                "CRITICAL"
            ),
        },
        "summary": {
            "typeDistribution": type_dist,
            "ambiguousProducts": ambiguous,
            "highRetrieval": sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] >= 75),
            "lowRetrieval":  sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] < 40),
        },
        "perceptions": perceptions,
    }

    with open("data/perception.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    ok(f"Avg retrieval score: {avg_retrieval:.1f}/100")
    ok(f"Ambiguous products: {ambiguous}/30")
    ok("Saved → data/perception.json")
    return True


def run_recommender():
    section("STEP 4 — Generating recommendations")
    step("Building fix suggestions per product...")
    from src.recommender import generate_store_insights
    from src.recommender import recommend_for_product

    report         = load_json("data/report.json")
    perception_data = load_json("data/perception.json")
    perception_map = {p["handle"]: p for p in perception_data["perceptions"]}

    product_recs = []
    for product_result in report["products"]:
        handle     = product_result["handle"]
        perception = perception_map.get(handle, {
            "aiPerception": {"retrievalScore": 0, "perceivedType": "Unknown", "interpretation": ""}
        })
        product_recs.append(recommend_for_product(product_result, perception))

    product_recs.sort(key=lambda x: x["currentScore"])
    store_insights = generate_store_insights(report, perception_data)

    output = {
        "meta": {
            "generatedAt":  datetime.now().isoformat(),
            "store":        report["reportMeta"]["store"],
            "avgScore":     report["reportMeta"]["avgQualityScore"],
            "storeGrade":   report["reportMeta"]["storeGrade"],
            "avgRetrieval": perception_data["meta"]["avgRetrievalScore"],
        },
        "storeInsights": store_insights,
        "products":      product_recs,
    }

    with open("data/recommendations.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    ok(f"Generated recommendations for {len(product_recs)} products")
    ok("Saved → data/recommendations.json")
    return True


def run_enhancer():
    section("STEP 5 — LLM Enhancement (Gemini)")
    step("Sending products to Gemini for content improvement...")
    from src.llm_enhancer import enhance_all_products
    result = enhance_all_products()
    ok(f"Enhanced: {result['stats']['enhanced']} | Failed: {result['stats']['failed']}")
    ok("Saved → data/enhanced.json")
    return True


def run_writer():
    section("STEP 6 — Applying changes to Shopify")
    step("Pushing enhanced content via Admin API...")
    from src.shopify_writer import apply_all_enhanced
    result = apply_all_enhanced()
    ok(f"Applied: {result['successful']} | Failed: {result['failed']}")
    ok("Saved → data/write_results.json")
    return True


def run_server():
    section("STEP 7 — Launching Dashboard")
    step("Starting Flask server at http://localhost:5000 ...")
    print("\n  Press Ctrl+C to stop the server.\n")
    os.system("python src/reporter/app.py")


# ── Summary printer ───────────────────────────────────────────────────────────

def print_summary():
    section("PIPELINE COMPLETE — SUMMARY")
    try:
        report     = load_json("data/report.json")
        perception = load_json("data/perception.json")
        recs       = load_json("data/recommendations.json")

        meta = report["reportMeta"]
        print(f"""
  Store          : {meta['store']}.myshopify.com
  Products       : {meta['productsAnalyzed']}
  Quality Score  : {meta['avgQualityScore']}/100 (Grade {meta['storeGrade']})
  AI Retrieval   : {perception['meta']['avgRetrievalScore']}/100
  Visibility     : {perception['meta']['storeVisibility']}
  Ambiguous      : {perception['summary']['ambiguousProducts']} products

  Top Issues:""")
        for issue in report["summary"]["topIssues"][:5]:
            print(f"    {issue['code']:<35} {issue['count']} products")

        print(f"""
  Worst products (most urgent):""")
        for p in recs["products"][:3]:
            print(f"    [{p['grade']}] {p['title'][:45]:<45} score: {p['currentScore']}/100")

        print(f"\n  Open dashboard: python main.py --serve")
        print(f"{'─'*55}\n")
    except Exception as e:
        print(f"  Could not load summary: {e}")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"""
╔══════════════════════════════════════════════════════╗
║     AI Representation Optimizer — Pipeline Runner    ║
║     Store: together-stack.myshopify.com              ║
╚══════════════════════════════════════════════════════╝
    """)

    start = time.time()
    ok_so_far = True

    # Core pipeline — always runs
    ok_so_far = run_fetcher()    and ok_so_far
    ok_so_far = run_analyzer()   and ok_so_far
    ok_so_far = run_perception() and ok_so_far
    ok_so_far = run_recommender() and ok_so_far

    # Optional steps
    if args.enhance and ok_so_far:
        run_enhancer()

    if args.apply and ok_so_far:
        run_writer()

    elapsed = time.time() - start
    print(f"\n  Pipeline completed in {elapsed:.1f}s")

    print_summary()

    if args.serve:
        run_server()