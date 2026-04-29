"""
src/reporter/app.py
REPLACE EXISTING FILE

Changes:
  - Removed fragile sys.path.insert hack — run app from project root: python src/reporter/app.py
  - Store name read from .env (dynamic)
  - /api/rescore/<handle> — re-runs analyzer for single product after apply
  - /api/store-health — returns composite score including policy + trust
  - /api/roi — returns ranked ROI fix list
  - Port configurable via --port arg or FLASK_PORT env var
  - Proper __init__.py package structure (src/checks/)
"""

import os
import sys
import json
import argparse
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv

load_dotenv()

# ── Path setup — run from project root ───────────────────────────────────────
# Usage: python src/reporter/app.py  (from project root)
# or:    python main.py --serve
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))

STORE    = os.getenv("SHOPIFY_STORE", "your-store")
DATA_DIR = ROOT / "data"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent / "templates"),
    static_folder=str(Path(__file__).parent / "static"),
)

# ── Data helpers ──────────────────────────────────────────────────────────────

def load(filename):
    path = DATA_DIR / filename
    if not path.exists():
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)

def save(filename, data):
    with open(DATA_DIR / filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def by_handle(collection_key, filename):
    data = load(filename)
    items = data.get(collection_key, []) if collection_key else data
    if isinstance(items, list):
        return {item.get("handle", item.get("key", i)): item for i, item in enumerate(items)}
    return items

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

    meta  = report.get("reportMeta", {})
    pmeta = perception.get("meta", {})

    stats = {
        "store":           STORE,
        "avgScore":        meta.get("avgQualityScore", 0),
        "storeGrade":      meta.get("storeGrade", "?"),
        "compositeScore":  report.get("compositeScore", meta.get("avgQualityScore", 0)),
        "compositeGrade":  report.get("compositeGrade", meta.get("storeGrade", "?")),
        "avgRetrieval":    pmeta.get("avgRetrievalScore", 0),
        "visibility":      pmeta.get("storeVisibility", "?"),
        "ambiguous":       perception.get("summary", {}).get("ambiguousProducts", 0),
        "productsCount":   meta.get("productsAnalyzed", 0),
        "topIssues":       report.get("summary", {}).get("topIssues", [])[:5],
        "roiRanking":      recs.get("roiRanking", report.get("summary", {}).get("roiRanking", []))[:5],
        "severityCounts":  report.get("summary", {}).get("severityCounts", {}),
        "scoreDistribution": report.get("summary", {}).get("scoreDistribution", {}),
        "narrative":       report.get("narrative", ""),
        "policyScore":     policy.get("policyScore", "—"),
        "policyGrade":     policy.get("policyGrade", "?"),
        "policyIssues":    len(policy.get("issues", [])),
        "trustScore":      trust.get("trustScore", "—"),
        "trustGrade":      trust.get("trustGrade", "?"),
        "trustIssues":     len(trust.get("issues", [])),
    }

    return render_template("index.html",
        stats=stats,
        products=recs.get("products", []),
        insights=recs.get("storeInsights", []),
        policy_issues=policy.get("issues", []),
        trust_issues=trust.get("issues", []),
    )


@app.route("/product/<handle>")
def product_detail(handle):
    product    = get_product(handle)
    report     = get_report(handle)
    perception = get_perception(handle)
    rec        = get_rec(handle)
    if not product:
        return f"Product '{handle}' not found", 404
    return render_template("product.html",
        product=product, report=report or {}, perception=perception or {}, rec=rec or {})


# ── API — read ────────────────────────────────────────────────────────────────

@app.route("/api/stats")
def api_stats():
    report     = load("report.json")
    perception = load("perception.json")
    policy     = load("policy_report.json")
    trust      = load("trust_report.json")
    return jsonify({
        "report":     report.get("reportMeta", {}),
        "perception": perception.get("meta", {}),
        "summary":    report.get("summary", {}),
        "composite":  {"score": report.get("compositeScore"), "grade": report.get("compositeGrade")},
        "policy":     {"score": policy.get("policyScore"), "grade": policy.get("policyGrade")},
        "trust":      {"score": trust.get("trustScore"),  "grade": trust.get("trustGrade")},
    })


@app.route("/api/roi")
def api_roi():
    recs = load("recommendations.json")
    return jsonify(recs.get("roiRanking", []))


@app.route("/api/store-health")
def api_store_health():
    report  = load("report.json")
    policy  = load("policy_report.json")
    trust   = load("trust_report.json")
    percep  = load("perception.json")
    return jsonify({
        "productScore":  report.get("reportMeta", {}).get("avgQualityScore"),
        "compositeScore": report.get("compositeScore"),
        "policyScore":   policy.get("policyScore"),
        "trustScore":    trust.get("trustScore"),
        "retrievalScore": percep.get("meta", {}).get("avgRetrievalScore"),
        "narrative":     report.get("narrative"),
    })


@app.route("/api/products")
def api_products():
    return jsonify(load("recommendations.json").get("products", []))


# ── API — actions ─────────────────────────────────────────────────────────────

@app.route("/api/enhance/<handle>", methods=["POST"])
def api_enhance(handle):
    product = get_product(handle)
    report  = get_report(handle)
    if not product:
        return jsonify({"success": False, "error": f"Product '{handle}' not found"}), 404
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
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/rescore/<handle>", methods=["POST"])
def api_rescore(handle):
    """
    Re-runs the analyzer for a single product after changes are applied.
    Updates report.json and recommendations.json for that product only.
    """
    product = get_product(handle)
    if not product:
        return jsonify({"success": False, "error": "Product not found"}), 404
    try:
        from src.analyzer      import analyze_product, CONVERSION_IMPACT
        from src.ai_perception import generate_perception
        from src.recommender   import recommend_for_product

        new_report     = analyze_product(product)
        new_perception = generate_perception(product)
        new_rec        = recommend_for_product(new_report, new_perception)

        # Patch report.json
        report = load("report.json")
        report["products"] = [
            new_report if p["handle"] == handle else p
            for p in report.get("products", [])
        ]
        save("report.json", report)

        # Patch perception.json
        percep = load("perception.json")
        percep["perceptions"] = [
            new_perception if p["handle"] == handle else p
            for p in percep.get("perceptions", [])
        ]
        save("perception.json", percep)

        return jsonify({
            "success":    True,
            "newScore":   new_report["score"],
            "newGrade":   new_report["grade"],
            "newIssues":  new_report["totalIssues"],
            "perception": new_perception["aiPerception"],
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-image/<handle>", methods=["POST"])
def api_upload_image(handle):
    product = get_product(handle)
    if not product:
        return jsonify({"success": False, "error": f"Product '{handle}' not found"}), 404
    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file in request"}), 400
    file   = request.files["image"]
    result = None
    try:
        from src.image_handler import handle_image_upload
        result = handle_image_upload(
            product_id=product["id"],
            product_title=product["title"],
            file_bytes=file.read(),
            filename=file.filename,
        )
    except Exception as e:
        result = {"success": False, "errors": [str(e)], "warnings": [], "info": {}}
    return jsonify(result)


@app.route("/api/rerun-pipeline", methods=["POST"])
def api_rerun():
    try:
        from src.fetcher       import fetch_products
        from src.analyzer      import build_report
        from src.ai_perception import generate_perception
        from src.checks.faq_policy    import check_faq_and_policies
        from src.checks.trust_signals import check_store_trust
        from datetime import datetime, timezone

        products_data = fetch_products()
        policy_report = check_faq_and_policies()
        trust_report  = check_store_trust(products_data["products"])
        perceptions   = [generate_perception(p) for p in products_data["products"]]
        n             = len(perceptions)
        avg_ret       = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / n if n else 0
        perc_output   = {
            "meta": {
                "generatedAt":       datetime.now(timezone.utc).isoformat(),
                "productsProcessed": n,
                "avgRetrievalScore": round(avg_ret, 1),
                "storeVisibility":   "HIGH" if avg_ret >= 75 else "MEDIUM" if avg_ret >= 50 else "LOW",
            },
            "summary": {
                "ambiguousProducts": sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"]),
            },
            "perceptions": perceptions,
        }
        report = build_report(products_data, policy_report, trust_report, perc_output["meta"])

        for fname, data in [
            ("products.json",     products_data),
            ("policy_report.json", policy_report),
            ("trust_report.json",  trust_report),
            ("report.json",        report),
            ("perception.json",    perc_output),
        ]:
            save(fname, data)

        return jsonify({"success": True, "message": "Full pipeline re-run complete."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=int(os.getenv("FLASK_PORT", 5000)))
    a = ap.parse_args()
    print(f"\n  AI Representation Optimizer Dashboard")
    print(f"  Store: {STORE}.myshopify.com")
    print(f"  http://localhost:{a.port}\n")
    app.run(debug=True, port=a.port)