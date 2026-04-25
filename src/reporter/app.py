"""
reporter/app.py
Flask web dashboard for the AI Representation Optimizer.
Serves the UI and exposes API endpoints for one-click actions.
"""

import os
import sys
import json
from flask import Flask, render_template, jsonify, request

# Allow imports from project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from src.llm_enhancer   import enhance_product
from src.shopify_writer import apply_enhanced_content
from src.image_handler  import handle_image_upload

app = Flask(__name__, template_folder="templates", static_folder="static")

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data")


# ── Data loaders ──────────────────────────────────────────────────────────────

def load(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return {}
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def get_product_by_handle(handle):
    products = load("products.json").get("products", [])
    return next((p for p in products if p["handle"] == handle), None)


def get_report_for_handle(handle):
    products = load("report.json").get("products", [])
    return next((p for p in products if p["handle"] == handle), None)


def get_perception_for_handle(handle):
    perceptions = load("perception.json").get("perceptions", [])
    return next((p for p in perceptions if p["handle"] == handle), None)


def get_recommendation_for_handle(handle):
    products = load("recommendations.json").get("products", [])
    return next((p for p in products if p["handle"] == handle), None)


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    report      = load("report.json")
    perception  = load("perception.json")
    recs        = load("recommendations.json")

    meta = report.get("reportMeta", {})
    pmeta = perception.get("meta", {})

    stats = {
        "store":          meta.get("store", ""),
        "avgScore":       meta.get("avgQualityScore", 0),
        "storeGrade":     meta.get("storeGrade", "?"),
        "avgRetrieval":   pmeta.get("avgRetrievalScore", 0),
        "visibility":     pmeta.get("storeVisibility", "?"),
        "ambiguous":      perception.get("summary", {}).get("ambiguousProducts", 0),
        "productsCount":  meta.get("productsAnalyzed", 0),
        "topIssues":      report.get("summary", {}).get("topIssues", [])[:5],
        "severityCounts": report.get("summary", {}).get("severityCounts", {}),
        "scoreDistribution": report.get("summary", {}).get("scoreDistribution", {}),
    }

    products = recs.get("products", [])
    insights = recs.get("storeInsights", [])

    return render_template("index.html", stats=stats, products=products, insights=insights)


@app.route("/product/<handle>")
def product_detail(handle):
    product    = get_product_by_handle(handle)
    report     = get_report_for_handle(handle)
    perception = get_perception_for_handle(handle)
    rec        = get_recommendation_for_handle(handle)

    if not product:
        return f"Product '{handle}' not found", 404

    return render_template(
        "product.html",
        product=product,
        report=report or {},
        perception=perception or {},
        rec=rec or {},
    )


# ── API endpoints ─────────────────────────────────────────────────────────────

@app.route("/api/enhance/<handle>", methods=["POST"])
def api_enhance(handle):
    """Generate AI-improved content for a product (preview only, no write)."""
    product = get_product_by_handle(handle)
    report  = get_report_for_handle(handle)

    if not product:
        return jsonify({"success": False, "error": f"Product '{handle}' not found"}), 404

    issues = report.get("issues", []) if report else []

    try:
        enhanced = enhance_product(product, issues)
        return jsonify({"success": True, "enhanced": enhanced})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/apply/<handle>", methods=["POST"])
def api_apply(handle):
    """Apply enhanced content to Shopify (write)."""
    data       = request.get_json()
    enhanced   = data.get("enhanced")
    product    = get_product_by_handle(handle)

    if not product or not enhanced:
        return jsonify({"success": False, "error": "Missing product or enhanced data"}), 400

    try:
        result = apply_enhanced_content(product["id"], enhanced)
        return jsonify(result)
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/upload-image/<handle>", methods=["POST"])
def api_upload_image(handle):
    """Validate and upload a product image."""
    product = get_product_by_handle(handle)
    if not product:
        return jsonify({"success": False, "error": f"Product '{handle}' not found"}), 404

    if "image" not in request.files:
        return jsonify({"success": False, "error": "No image file in request"}), 400

    file        = request.files["image"]
    file_bytes  = file.read()
    filename    = file.filename

    result = handle_image_upload(
        product_id=product["id"],
        product_title=product["title"],
        file_bytes=file_bytes,
        filename=filename,
    )
    return jsonify(result)


@app.route("/api/products")
def api_products():
    """Return all products with their scores."""
    recs = load("recommendations.json")
    return jsonify(recs.get("products", []))


@app.route("/api/stats")
def api_stats():
    """Return store-level stats."""
    report     = load("report.json")
    perception = load("perception.json")
    return jsonify({
        "report":     report.get("reportMeta", {}),
        "perception": perception.get("meta", {}),
        "summary":    report.get("summary", {}),
    })


@app.route("/api/rerun-pipeline", methods=["POST"])
def api_rerun():
    """Re-fetch and re-analyze all products."""
    try:
        from src.fetcher       import fetch_products
        from src.analyzer      import build_report
        from src.ai_perception import generate_perception
        from src.recommender   import recommend_for_product, generate_store_insights
        from datetime          import datetime

        products_data = fetch_products()
        report        = build_report(products_data)

        perceptions = [generate_perception(p) for p in products_data["products"]]
        avg_retrieval = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / len(perceptions)

        perception_output = {
            "meta": {
                "generatedAt":       datetime.now().isoformat(),
                "productsProcessed": len(perceptions),
                "avgRetrievalScore": round(avg_retrieval, 1),
                "storeVisibility":   "HIGH" if avg_retrieval >= 75 else "MEDIUM" if avg_retrieval >= 50 else "LOW",
            },
            "summary": {
                "ambiguousProducts": sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"]),
                "highRetrieval":     sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] >= 75),
                "lowRetrieval":      sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] < 40),
            },
            "perceptions": perceptions,
        }

        # Generate new recommendations to update individual product scores
        perception_map = {p["handle"]: p for p in perceptions}
        product_recs = []
        for product_result in report["products"]:
            handle = product_result["handle"]
            perception = perception_map.get(handle, {
                "aiPerception": {"retrievalScore": 0, "perceivedType": "Unknown", "interpretation": ""}
            })
            product_recs.append(recommend_for_product(product_result, perception))

        product_recs.sort(key=lambda x: x["currentScore"])
        store_insights = generate_store_insights(report, perception_output)

        rec_output = {
            "meta": {
                "generatedAt":  datetime.now().isoformat(),
                "store":        report["reportMeta"]["store"],
                "avgScore":     report["reportMeta"]["avgQualityScore"],
                "storeGrade":   report["reportMeta"]["storeGrade"],
                "avgRetrieval": perception_output["meta"]["avgRetrievalScore"],
            },
            "storeInsights": store_insights,
            "products":      product_recs,
        }

        for path, data in [
            ("data/report.json",     report),
            ("data/perception.json", perception_output),
            ("data/recommendations.json", rec_output),
        ]:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        return jsonify({"success": True, "message": "Pipeline re-run complete."})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("\n  AI Representation Optimizer Dashboard")
    print("  http://localhost:5000\n")
    app.run(debug=True, port=5000)