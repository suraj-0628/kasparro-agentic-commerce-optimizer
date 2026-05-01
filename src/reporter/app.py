"""
src/reporter/app.py — REPLACE EXISTING

Fixes:
  - In-memory cache for JSON files (not reading from disk on every request)
  - /api/undo/<handle> — revert last applied change
  - /api/query-simulation — return query coverage data
  - /api/competitive — return benchmarking data
  - Safe startup: creates placeholder data if pipeline hasn't run yet
  - Port from --port arg or FLASK_PORT env
"""

import os
import sys
import json
import time
import argparse
from pathlib import Path
from functools import lru_cache
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

load_dotenv()

ROOT     = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

STORE    = os.getenv("SHOPIFY_STORE", "your-store")
DATA_DIR = ROOT / "data"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# ── Simple in-memory cache ────────────────────────────────────────────────────
_cache     = {}
_cache_ttl = {}
CACHE_SECS = 30  # refresh every 30s or on demand


def load(filename: str, max_age: int = CACHE_SECS) -> dict:
    now  = time.time()
    path = DATA_DIR / filename
    if filename in _cache and (now - _cache_ttl.get(filename, 0)) < max_age:
        return _cache[filename]
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    _cache[filename]     = data
    _cache_ttl[filename] = now
    return data


def invalidate_cache():
    _cache.clear()
    _cache_ttl.clear()


def save_data(filename: str, data: dict):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    _cache.pop(filename, None)


# ── Safe startup — create placeholder files if missing ───────────────────────

def ensure_data_files():
    """Prevents FileNotFoundError when dashboard is opened before pipeline runs."""
    DATA_DIR.mkdir(exist_ok=True)
    placeholders = {
        "products.json":          {"store": STORE, "productCount": 0, "products": []},
        "report.json":            {"reportMeta": {"store": STORE, "avgQualityScore": 0, "storeGrade": "?", "productsAnalyzed": 0}, "summary": {"topIssues": [], "severityCounts": {}, "roiRanking": []}, "products": []},
        "perception.json":        {"meta": {"avgRetrievalScore": 0, "storeVisibility": "UNKNOWN"}, "summary": {"ambiguousProducts": 0}, "perceptions": []},
        "recommendations.json":   {"meta": {}, "storeInsights": [], "roiRanking": [], "products": []},
        "policy_report.json":     {"policyScore": 0, "policyGrade": "?", "totalIssues": 0, "issues": []},
        "trust_report.json":      {"trustScore": 0, "trustGrade": "?", "totalIssues": 0, "issues": []},
        "query_simulation.json":  {"totalQueries": 0, "coverageRate": 0, "zeroMatchQueries": [], "queryResults": []},
        "competitive_context.json": {"scorePercentile": 0, "industryMedian": 52},
    }
    for fname, default in placeholders.items():
        fpath = DATA_DIR / fname
        if not fpath.exists():
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(default, f, indent=2)


ensure_data_files()

# ── Helpers ───────────────────────────────────────────────────────────────────

def get_product(handle):
    return next((p for p in load("products.json").get("products", []) if p["handle"] == handle), None)

def get_report(handle):
    return next((p for p in load("report.json").get("products", []) if p["handle"] == handle), None)

def get_perception(handle):
    return next((p for p in load("perception.json").get("perceptions", []) if p["handle"] == handle), None)

def get_rec(handle):
    return next((p for p in load("recommendations.json").get("products", []) if p["handle"] == handle), None)


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    report      = load("report.json")
    perception  = load("perception.json")
    recs        = load("recommendations.json")
    policy      = load("policy_report.json")
    trust       = load("trust_report.json")
    qsim        = load("query_simulation.json")
    competitive = load("competitive_context.json")

    meta  = report.get("reportMeta", {})
    pmeta = perception.get("meta", {})

    pipeline_run = meta.get("productsAnalyzed", 0) > 0

    stats = {
        "store":            STORE,
        "pipelineRun":      pipeline_run,
        "avgScore":         meta.get("avgQualityScore", 0),
        "storeGrade":       meta.get("storeGrade", "?"),
        "compositeScore":   report.get("compositeScore", 0),
        "compositeGrade":   report.get("compositeGrade", "?"),
        "avgRetrieval":     pmeta.get("avgRetrievalScore", 0),
        "visibility":       pmeta.get("storeVisibility", "?"),
        "ambiguous":        perception.get("summary", {}).get("ambiguousProducts", 0),
        "productsCount":    meta.get("productsAnalyzed", 0),
        "topIssues":        report.get("summary", {}).get("topIssues", [])[:5],
        "roiRanking":       recs.get("roiRanking", report.get("summary", {}).get("roiRanking", []))[:6],
        "severityCounts":   report.get("summary", {}).get("severityCounts", {}),
        "scoreDistribution": report.get("summary", {}).get("scoreDistribution", {}),
        "narrative":        report.get("narrative", ""),
        "policyScore":      policy.get("policyScore", 0),
        "policyGrade":      policy.get("policyGrade", "?"),
        "policyIssues":     len(policy.get("issues", [])),
        "trustScore":       trust.get("trustScore", 0),
        "trustGrade":       trust.get("trustGrade", "?"),
        "trustIssues":      len(trust.get("issues", [])),
        "queryCoverage":    qsim.get("coverageRate", 0),
        "queryCovered":     qsim.get("coveredQueries", 0),
        "queryTotal":       qsim.get("totalQueries", 0),
        "zeroMatchCount":   len(qsim.get("zeroMatchQueries", [])),
        "competitive":      competitive
    }

    return render_template("index.html",
        stats=stats,
        products=recs.get("products", []),
        insights=recs.get("storeInsights", []),
        policy_issues=policy.get("issues", []),
        trust_issues=trust.get("issues", []),
        zero_match_queries=qsim.get("zeroMatchQueries", [])[:5],
    )


@app.route("/product/<handle>")
def product_detail(handle):
    product    = get_product(handle)
    report     = get_report(handle)
    perception = get_perception(handle)
    rec        = get_rec(handle)
    qsim       = load("query_simulation.json")
    prod_cov   = qsim.get("productCoverage", {}).get(handle, {})

    if not product:
        return f"Product '{handle}' not found — run python main.py first", 404

    return render_template("product.html",
        product=product,
        report=report or {},
        perception=perception or {},
        rec=rec or {},
        query_coverage=prod_cov,
    )


# ── API — data ────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    return jsonify({
        "report":      load("report.json").get("reportMeta", {}),
        "perception":  load("perception.json").get("meta", {}),
        "summary":     load("report.json").get("summary", {}),
        "policy":      {"score": load("policy_report.json").get("policyScore"), "grade": load("policy_report.json").get("policyGrade")},
        "trust":       {"score": load("trust_report.json").get("trustScore"),   "grade": load("trust_report.json").get("trustGrade")},
        "competitive": load("competitive_context.json"),
        "querySim":    {k: load("query_simulation.json").get(k) for k in ["coverageRate", "coveredQueries", "totalQueries", "zeroMatchQueries"]},
    })


@app.route("/api/query-simulation")
def api_query_sim():
    return jsonify(load("query_simulation.json"))


@app.route("/api/competitive")
def api_competitive():
    return jsonify(load("competitive_context.json"))


@app.route("/api/roi")
def api_roi():
    return jsonify(load("recommendations.json").get("roiRanking", []))


@app.route("/api/products")
def api_products():
    return jsonify(load("recommendations.json").get("products", []))


@app.route("/api/changelog")
def api_changelog():
    return jsonify(load("changelog.json") if (DATA_DIR / "changelog.json").exists() else [])


# ── API — actions ─────────────────────────────────────────────────────────────

@app.route("/api/enhance/<handle>", methods=["POST"])
def api_enhance(handle):
    product = get_product(handle)
    report  = get_report(handle)
    if not product:
        return jsonify({"success": False, "error": "Product not found — run pipeline first"}), 404
    try:
        from src.llm_enhancer import enhance_product
        enhanced = enhance_product(product, report.get("issues", []) if report else [])
        return jsonify({"success": True, "enhanced": enhanced})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/apply/<handle>", methods=["POST"])
def api_apply(handle):
    data     = request.get_json()
    enhanced = data.get("enhanced")
    product  = get_product(handle)
    if not product or not enhanced:
        return jsonify({"success": False, "error": "Missing product or enhanced data"}), 400
    try:
        from src.shopify_writer import apply_enhanced_content
        result = apply_enhanced_content(product["id"], enhanced)
        
        if result.get("success"):
            import re
            # Update local products.json so rescore works on new data
            products_data = load("products.json")
            for p in products_data["products"]:
                if p["handle"] == handle:
                    p["title"] = enhanced.get("title", p["title"])
                    if "descriptionHtml" in enhanced:
                        p["descriptionHtml"] = enhanced["descriptionHtml"]
                        clean = re.sub(r'<[^>]+>', ' ', p["descriptionHtml"])
                        p["descriptionPlain"] = re.sub(r'\s+', ' ', clean).strip()
                        p["descriptionWordCount"] = len(p["descriptionPlain"].split())
                    p["tags"] = enhanced.get("tags", p["tags"])
                    if "seo" in enhanced:
                        p["seo"] = enhanced["seo"]
                    if enhanced.get("product_type"):
                        new_type = str(enhanced["product_type"]).strip()
                        p["productType"] = new_type
                        p["category"] = {
                            "name":     new_type,
                            "fullName": new_type,
                            "source":   "productType"
                        }
                    
                    # Update SKUs locally
                    suggested_variants = enhanced.get("variants")
                    if isinstance(suggested_variants, list):
                        for ev in suggested_variants:
                            for v in p.get("variants", []):
                                if v.get("id") == ev.get("id"):
                                    v["sku"] = ev.get("sku", "")
                    break
            save_data("products.json", products_data)
            
        invalidate_cache()
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500




@app.route("/api/rescore/<handle>", methods=["POST"])
def api_rescore(handle):
    """Re-run analyzer for a single product after changes are applied."""
    product = get_product(handle)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404
    try:
        from src.analyzer      import analyze_product
        from src.ai_perception import generate_perception
        from src.recommender   import recommend_for_product, recommend_for_store

        # 1. Analyze single product
        new_report     = analyze_product(product)
        new_perception = generate_perception(product)

        # 2. Update report.json and recalculate averages
        report = load("report.json")
        report["products"] = [new_report if p["handle"] == handle else p for p in report.get("products", [])]
        
        scores = [p["score"] for p in report["products"]]
        avg    = round(sum(scores) / len(scores), 1) if scores else 0
        report["reportMeta"]["avgQualityScore"] = avg
        report["reportMeta"]["storeGrade"]      = "A" if avg >= 80 else "B" if avg >= 60 else "C" if avg >= 40 else "F"
        
        # 3. Update perception.json and recalculate averages
        percep = load("perception.json")
        percep["perceptions"] = [new_perception if p["handle"] == handle else p for p in percep.get("perceptions", [])]
        
        rets    = [p["aiPerception"]["retrievalScore"] for p in percep["perceptions"]]
        avg_ret = round(sum(rets) / len(rets), 1) if rets else 0
        percep["meta"]["avgRetrievalScore"] = avg_ret
        percep["meta"]["storeVisibility"]   = "HIGH" if avg_ret >= 75 else "MEDIUM" if avg_ret >= 50 else "LOW"
        percep["summary"]["ambiguousProducts"] = sum(1 for p in percep["perceptions"] if p["aiPerception"]["isAmbiguous"])
        
        # 4. Rebuild recommendations.json for the whole store
        new_recs = recommend_for_store(report, percep)
        
        # Save all
        save_data("report.json", report)
        save_data("perception.json", percep)
        save_data("recommendations.json", new_recs)

        # Trigger Fast-Simulation for search visibility
        from src.checks.query_simulator import simulate_queries
        from src.analyzer import build_report
        products_data = load("products.json")
        policy_report = load("policy_report.json")
        trust_report = load("trust_report.json")
        perc_data = load("perception.json")
        
        # Rerun simulation
        new_qsim = simulate_queries(products_data["products"])
        save_data("query_simulation.json", new_qsim)
        
        # REBUILD REPORT so UI sees the new visibility %
        new_report_full = build_report(products_data, policy_report, trust_report, perc_data["meta"])
        save_data("report.json", new_report_full)

        invalidate_cache()
        return jsonify({
            "success":    True,
            "newScore":   new_report["score"],
            "newGrade":   new_report["grade"],
            "newIssues":  new_report["totalIssues"],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-image/<handle>", methods=["POST"])
def api_upload_image(handle):
    product = get_product(handle)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image in request"}), 400
    file = request.files["image"]
    try:
        from src.image_handler import handle_image_upload
        result = handle_image_upload(
            product_id=product["id"],
            product_title=product["title"],
            file_bytes=file.read(),
            filename=file.filename,
        )
        
        if result.get("success"):
            # Instant Sync: Update local products.json
            products_data = load("products.json")
            for p in products_data["products"]:
                if p["handle"] == handle:
                    p["imageCount"] = p.get("imageCount", 0) + 1
                    p["hasImages"] = True
                    # Add a placeholder image URL so UI doesn't look empty
                    if not p.get("images"): p["images"] = []
                    p["images"].append({"url": "https://cdn.shopify.com/s/files/placeholder.jpg", "altText": "Newly Uploaded"})
                    break
            save_data("products.json", products_data)
            invalidate_cache()

        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rerun-pipeline", methods=["POST"])
def api_rerun():
    try:
        from src.fetcher       import fetch_products
        from src.analyzer      import build_report
        from src.ai_perception import generate_perception
        from src.checks.faq_policy    import check_faq_and_policies
        from src.checks.trust_signals import check_store_trust
        from src.checks.query_simulator    import simulate_queries
        from src.checks.competitor_baseline import generate_competitive_context
        from src.recommender   import recommend_for_store
        from datetime import datetime, timezone

        products_data  = fetch_products()
        policy_report  = check_faq_and_policies()
        trust_report   = check_store_trust(products_data["products"])
        query_sim      = simulate_queries(products_data["products"])
        perceptions    = [generate_perception(p) for p in products_data["products"]]
        n              = len(perceptions)
        avg_ret        = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / n if n else 0
        perc_out       = {
            "meta": {
                "generatedAt":       datetime.now(timezone.utc).isoformat(),
                "productsProcessed": n,
                "avgRetrievalScore": round(avg_ret, 1),
                "storeVisibility":   "HIGH" if avg_ret >= 75 else "MEDIUM" if avg_ret >= 50 else "LOW",
            },
            "summary": {"ambiguousProducts": sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"])},
            "perceptions": perceptions,
        }
        report = build_report(products_data, policy_report, trust_report, perc_out["meta"])
        recs   = recommend_for_store(report, perc_out)
        competitive = generate_competitive_context(
            report["reportMeta"]["avgQualityScore"], avg_ret, products_data["products"]
        )

        for fname, data in [
            ("products.json", products_data), ("policy_report.json", policy_report),
            ("trust_report.json", trust_report), ("query_simulation.json", query_sim),
            ("perception.json", perc_out), ("report.json", report),
            ("recommendations.json", recs), ("competitive_context.json", competitive),
        ]:
            save_data(fname, data)

        invalidate_cache()
        return jsonify({"success": True, "message": "Full re-analysis complete."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fix-sku/<handle>", methods=["POST"])
def api_fix_sku(handle):
    try:
        from src.llm_enhancer import generate_sku
        from src.shopify_writer import update_variant_sku
        
        products_data = load("products.json")
        product = next((p for p in products_data["products"] if p["handle"] == handle), None)
        if not product:
            return jsonify({"success": False, "error": "Product not found"}), 404
        
        results = []
        for variant in product.get("variants", []):
            if not variant.get("sku"):
                new_sku = generate_sku(product["title"], product.get("vendor", "GEN"), variant.get("title", ""))
                res = update_variant_sku(variant["id"], new_sku)
                if res.get("success"):
                    variant["sku"] = new_sku
                results.append(res)
        
        save_data("products.json", products_data)
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fix-policy-health", methods=["POST"])
def api_fix_policies():
    try:
        from src.llm_enhancer import generate_policy
        from src.shopify_writer import update_shop_policy, create_page
        
        policy_report = load("policy_report.json")
        issues = policy_report.get("issues", [])
        
        # Mapping UI issues to GQL types for legal policies
        legal_map = {
            "RETURN_POLICY":   "REFUND_POLICY",
            "PRIVACY_POLICY":  "PRIVACY_POLICY",
            "SHIPPING_POLICY": "SHIPPING_POLICY",
            "TERMS_OF_SERVICE": "TERMS_OF_SERVICE"
        }
        
        results = []
        for issue in issues:
            code = issue.get("code", "")
            m_type = issue.get("type")
            
            # Fallback for older reports missing the 'type' field
            if not m_type:
                if "RETURN" in code: m_type = "RETURN_POLICY"
                elif "SHIPPING" in code: m_type = "SHIPPING_POLICY"
                elif "PRIVACY" in code: m_type = "PRIVACY_POLICY"
                elif "FAQ" in code: m_type = "FAQ"
            
            if not m_type: continue
            
            # Handle Legal Policies
            if m_type in legal_map:
                gql_type = legal_map[m_type]
                html = generate_policy(m_type, STORE)
                res  = update_shop_policy(gql_type, html)
                results.append({"type": m_type, "res": res})
            
            # Handle FAQ (Creating as a Page)
            elif m_type == "FAQ":
                from src.llm_enhancer import generate_policy # Reusing for FAQ
                html = generate_policy("FAQ", STORE)
                res  = create_page("Frequently Asked Questions", html)
                results.append({"type": "FAQ", "res": res})
        
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fix-trust-gaps", methods=["POST"])
def api_fix_trust():
    try:
        from src.llm_enhancer import generate_about_us
        from src.shopify_writer import create_page
        
        # Find if 'About Us' is missing
        trust_report = load("trust_report.json")
        is_about_missing = any("About Us" in i["message"] for i in trust_report.get("issues", []))
        
        if is_about_missing:
            html = generate_about_us(STORE, "General E-commerce")
            res  = create_page("About Us", html)
            return jsonify({"success": True, "result": res})
        
        return jsonify({"success": True, "message": "No major trust gaps found or already fixed."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/fix-store-wide", methods=["POST"])
def api_fix_all():
    """
    MASTER FIX: Orchestrates Policies, Trust, and all SKUs in one go.
    """
    try:
        results = {"policies": None, "trust": None, "skus": []}
        
        # 1. Fix Policies
        results["policies"] = api_fix_policies().get_json()
        
        # 2. Fix Trust
        results["trust"] = api_fix_trust().get_json()
        
        # 3. Fix ALL SKUs across entire catalog
        from src.llm_enhancer import generate_sku
        from src.shopify_writer import update_variant_sku
        products_data = load("products.json")
        
        sku_count = 0
        for product in products_data.get("products", []):
            for variant in product.get("variants", []):
                if not variant.get("sku"):
                    new_sku = generate_sku(product["title"], product.get("vendor", "GEN"), variant.get("title", ""))
                    update_variant_sku(variant["id"], new_sku)
                    sku_count += 1
        
        results["sku_summary"] = f"Generated {sku_count} SKUs across store."
        
        return jsonify({"success": True, "results": results})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.getenv("FLASK_PORT", 5000)))
    a = ap.parse_args()
    print(f"\n  AI Representation Optimizer — {STORE}.myshopify.com")
    print(f"  http://localhost:{a.port}\n")
    app.run(debug=True, port=a.port)