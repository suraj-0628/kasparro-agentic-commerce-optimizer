"""
main.py — REPLACE EXISTING

New in this version:
  - Query simulation step (shows which AI searches the store misses)
  - Competitive context step (places score in industry percentile)
  - Dashboard-safe: creates empty data files if pipeline hasn't run yet
  - All hardcoded values removed — everything from .env
  - One failure per step doesn't kill the whole pipeline
"""

import sys
import os
import json
import time
import argparse
from datetime import datetime, timezone
from pathlib import Path

# Ensure project root is in sys.path so 'from src.x import y' works
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Ensure stdout uses utf-8 for box drawing characters on Windows
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

STORE = os.getenv("SHOPIFY_STORE", "your-store")
DATA  = Path("data")
DATA.mkdir(exist_ok=True)

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser(description="AI Representation Optimizer")
parser.add_argument("--enhance", action="store_true")
parser.add_argument("--apply",   action="store_true")
parser.add_argument("--serve",   action="store_true")
parser.add_argument("--full",    action="store_true")
parser.add_argument("--port",    type=int, default=5000)
parser.add_argument("--skip-fetch", action="store_true", help="Use existing products.json")
args = parser.parse_args()
if args.full:
    args.enhance = args.apply = args.serve = True

# ── Helpers ───────────────────────────────────────────────────────────────────
def banner():
    w = 56
    print(f"\n╔{'═'*w}╗")
    print(f"║{'AI Representation Optimizer':^{w}}║")
    print(f"║{f'Store: {STORE}.myshopify.com':^{w}}║")
    print(f"║{datetime.now().strftime('%Y-%m-%d  %H:%M'):^{w}}║")
    print(f"╚{'═'*w}╝\n")

def section(t): print(f"\n{'─'*56}\n  {t}\n{'─'*56}")
def ok(m):      print(f"  ✓ {m}")
def warn(m):    print(f"  ⚠ {m}")
def fail(m):    print(f"  ✗ {m}")
def step(m):    print(f"\n  → {m}")

def save(filename, data):
    with open(DATA / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def load(filename):
    p = DATA / filename
    if not p.exists(): return {}
    with open(p, encoding="utf-8") as f: return json.load(f)

# ── Steps ─────────────────────────────────────────────────────────────────────

def run_fetcher():
    section("STEP 1 — Fetch products from Shopify")
    if args.skip_fetch and (DATA / "products.json").exists():
        warn("Skipping fetch — using existing products.json")
        return True
    step("Connecting to Shopify Admin GraphQL API...")
    try:
        from src.fetcher import fetch_products
        result = fetch_products()
        ok(f"Fetched {result['productCount']} products")
        cats = result.get("categoryStats", {})
        ok(f"Category sources: taxonomy={cats.get('usingTaxonomy',0)}, productType={cats.get('usingProductType',0)}, none={cats.get('noCategory',0)}")
        return True
    except Exception as e:
        fail(f"Fetcher: {e}")
        return False


def run_policy_check():
    section("STEP 2 — Policy & FAQ audit")
    step("Checking store pages and policies...")
    try:
        from src.checks.faq_policy import check_faq_and_policies
        result = check_faq_and_policies()
        save("policy_report.json", result)
        ok(f"Policy score: {result['policyScore']}/100 ({result['totalIssues']} issues)")
        return result
    except Exception as e:
        warn(f"Policy check skipped: {e}")
        return {"policyScore": 100, "policyGrade": "A", "totalIssues": 0, "issues": [], "details": {}, "pagesChecked": 0}


def run_trust_check(products_data):
    section("STEP 3 — Trust signal analysis")
    step("Checking brand, social proof, guarantees...")
    try:
        from src.checks.trust_signals import check_store_trust
        result = check_store_trust(products_data.get("products", []))
        save("trust_report.json", result)
        ok(f"Trust score: {result['trustScore']}/100 ({result['totalIssues']} issues)")
        return result
    except Exception as e:
        warn(f"Trust check skipped: {e}")
        return {"trustScore": 100, "trustGrade": "A", "totalIssues": 0, "issues": [], "details": {}}


def run_query_simulation(products_data):
    section("STEP 4 — AI search query simulation")
    step("Simulating high-intent Indian shopper queries...")
    try:
        from src.checks.query_simulator import simulate_queries
        result = simulate_queries(products_data.get("products", []))
        save("query_simulation.json", result)
        ok(f"Query coverage: {result['coveredQueries']}/{result['totalQueries']} ({result['coverageRate']}% — {result['coverageLabel']})")
        if result["zeroMatchQueries"]:
            warn(f"{len(result['zeroMatchQueries'])} queries return ZERO products from your store")
        return result
    except Exception as e:
        warn(f"Query simulation skipped: {e}")
        return {}


def run_perception(products_data):
    section("STEP 5 — AI perception simulation")
    step("Classifying products as AI agents would...")
    try:
        from src.ai_perception import generate_perception
        perceptions   = [generate_perception(p) for p in products_data.get("products", [])]
        n             = len(perceptions)
        avg_retrieval = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / n if n else 0
        ambiguous     = sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"])
        type_dist     = {}
        for p in perceptions:
            t = p["aiPerception"]["perceivedType"]
            type_dist[t] = type_dist.get(t, 0) + 1

        output = {
            "meta": {
                "generatedAt":       datetime.now(timezone.utc).isoformat(),
                "productsProcessed": n,
                "avgRetrievalScore": round(avg_retrieval, 1),
                "storeVisibility":   "HIGH" if avg_retrieval >= 75 else "MEDIUM" if avg_retrieval >= 50 else "LOW" if avg_retrieval >= 25 else "CRITICAL",
            },
            "summary": {
                "typeDistribution":  type_dist,
                "ambiguousProducts": ambiguous,
                "highRetrieval":     sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] >= 75),
                "lowRetrieval":      sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] < 40),
            },
            "perceptions": perceptions,
        }
        save("perception.json", output)
        ok(f"Avg retrieval: {avg_retrieval:.1f}/100 | Ambiguous: {ambiguous}/{n}")
        return output
    except Exception as e:
        fail(f"Perception: {e}")
        return {}


def run_analyzer(products_data, policy_report, trust_report, perception_meta):
    section("STEP 6 — Product quality analysis")
    n = products_data.get("productCount", len(products_data.get("products", [])))
    step(f"Running 23 rules across {n} products...")
    try:
        from src.analyzer import build_report
        report = build_report(products_data, policy_report, trust_report, perception_meta)
        save("report.json", report)
        meta = report["reportMeta"]
        sev  = report["summary"]["severityCounts"]
        ok(f"Score: {meta['avgQualityScore']}/100 ({meta['storeGrade']}) | Composite: {report.get('compositeScore','—')}/100")
        ok(f"CRITICAL:{sev.get('CRITICAL',0)} HIGH:{sev.get('HIGH',0)} MEDIUM:{sev.get('MEDIUM',0)} LOW:{sev.get('LOW',0)}")
        return report
    except Exception as e:
        fail(f"Analyzer: {e}")
        return None


def run_competitive_context(products_data, avg_score, avg_retrieval):
    section("STEP 7 — Competitive benchmarking")
    step("Placing your score in industry context...")
    try:
        from src.checks.competitor_baseline import generate_competitive_context
        result = generate_competitive_context(avg_score, avg_retrieval, products_data.get("products", []))
        save("competitive_context.json", result)
        ok(f"Percentile: {result['scorePercentile']}th — {result['scorePercentileLabel']}")
        ok(f"Industry median: {result['industryMedian']} | Top 25%: {result['industryTop25']} | You: {avg_score}")
        return result
    except Exception as e:
        warn(f"Competitive context skipped: {e}")
        return {}


def run_recommender(report, perception_data):
    section("STEP 8 — Recommendations")
    step("Building ranked action plan...")
    try:
        from src.recommender import recommend_for_product, generate_store_insights
        perception_map = {p["handle"]: p for p in perception_data.get("perceptions", [])}

        recs = []
        for pr in report.get("products", []):
            perc = perception_map.get(pr["handle"], {
                "aiPerception": {"retrievalScore": 0, "perceivedType": "Unknown", "interpretation": ""}
            })
            recs.append(recommend_for_product(pr, perc))
        recs.sort(key=lambda x: x["currentScore"])

        insights = generate_store_insights(report, perception_data)

        output = {
            "meta": {
                "generatedAt":  datetime.now(timezone.utc).isoformat(),
                "store":        report["reportMeta"]["store"],
                "avgScore":     report["reportMeta"]["avgQualityScore"],
                "storeGrade":   report["reportMeta"]["storeGrade"],
                "compositeScore": report.get("compositeScore"),
                "avgRetrieval": perception_data.get("meta", {}).get("avgRetrievalScore", 0),
                "narrative":    report.get("narrative", ""),
            },
            "storeInsights":  insights,
            "roiRanking":     report["summary"].get("roiRanking", []),
            "products":       recs,
        }
        save("recommendations.json", output)
        ok(f"Recommendations for {len(recs)} products | {len(insights)} insights")
        return output
    except Exception as e:
        fail(f"Recommender: {e}")
        return None


def run_enhancer():
    section("STEP 9 — LLM Enhancement (Gemini)")
    model = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
    step(f"Model: {model} | Rate limit: 1.5s between calls")
    try:
        from src.llm_enhancer import enhance_all_products
        result = enhance_all_products()
        stats  = result["stats"]
        ok(f"enhanced={stats['enhanced']} skipped={stats['skipped']} failed={stats['failed']}")
    except Exception as e:
        fail(f"Enhancer: {e}")


def run_writer():
    section("STEP 10 — Apply to Shopify")
    step("Pushing changes via Admin API (changelog saved before each write)...")
    try:
        from src.shopify_writer import apply_all_enhanced
        result = apply_all_enhanced()
        ok(f"applied={result['successful']} failed={result['failed']}")
        ok("Undo history saved to data/changelog.json")
    except Exception as e:
        fail(f"Writer: {e}")


def print_summary(report, perception_data, recs, competitive):
    section("PIPELINE COMPLETE")
    meta   = report["reportMeta"]
    pmeta  = perception_data.get("meta", {})
    qsim   = load("query_simulation.json")
    print(f"""
  Store          : {meta['store']}.myshopify.com
  Products       : {meta['productsAnalyzed']}
  Quality Score  : {meta['avgQualityScore']}/100 (Grade {meta['storeGrade']})
  Composite Score: {report.get('compositeScore','—')}/100
  AI Retrieval   : {pmeta.get('avgRetrievalScore','—')}/100
  Query Coverage : {qsim.get('coverageRate','—')}% of high-intent searches
  Percentile     : {competitive.get('scorePercentile','—')}th ({competitive.get('scorePercentileLabel','—')})

  {report.get('narrative','')}

  Top ROI fixes:""")
    for item in report["summary"].get("roiRanking", [])[:5]:
        print(f"    {item['code']:<35} {item['affectedProducts']} products  +{item['totalScoreLift']} pts")
    if recs:
        print(f"\n  Worst 3 products:")
        for p in recs.get("products", [])[:3]:
            print(f"    [{p['grade']}] {p['title'][:45]:<45} {p['currentScore']}/100")
    print(f"\n  Dashboard: python main.py --serve")
    print(f"{'─'*56}\n")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    banner()
    start = time.time()

    if not run_fetcher(): sys.exit(1)
    products_data = load("products.json")

    policy_report = run_policy_check()
    trust_report  = run_trust_check(products_data)
    query_sim     = run_query_simulation(products_data)
    perception    = run_perception(products_data)

    report = run_analyzer(
        products_data,
        policy_report,
        trust_report,
        perception.get("meta"),
    )
    if not report: sys.exit(1)

    avg_score     = report["reportMeta"]["avgQualityScore"]
    avg_retrieval = perception.get("meta", {}).get("avgRetrievalScore", 0)
    competitive   = run_competitive_context(products_data, avg_score, avg_retrieval)
    recs          = run_recommender(report, perception)

    if args.enhance: run_enhancer()
    if args.apply:   run_writer()

    print(f"\n  Completed in {time.time()-start:.1f}s")
    try:
        print_summary(report, perception, recs, competitive)
    except Exception: pass

    if args.serve:
        section(f"Dashboard → http://localhost:{args.port}")
        os.environ["FLASK_PORT"] = str(args.port)
        os.system(f"{sys.executable} src/reporter/app.py --port {args.port}")