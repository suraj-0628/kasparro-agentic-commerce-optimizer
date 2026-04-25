import json
import re
from datetime import datetime

# ── Type vocabulary ───────────────────────────────────────────────────────────

TYPE_VOCABULARY = [
    {"type": "T-Shirt / Top",         "keywords": ["tshirt", "t-shirt", "shirt", "top", "kurta", "blouse"]},
    {"type": "Jacket / Outerwear",    "keywords": ["jacket", "hoodie", "sweatshirt", "coat", "outerwear"]},
    {"type": "Footwear",              "keywords": ["shoe", "sneaker", "sandal", "boot", "slipper", "flip flop"]},
    {"type": "Skincare",              "keywords": ["cream", "serum", "moisturiser", "face wash", "sunscreen", "lotion"]},
    {"type": "Headphones / Earphones","keywords": ["headphone", "earphone", "earbud", "headset"]},
    {"type": "Speaker",               "keywords": ["speaker", "soundbar"]},
    {"type": "Smartwatch / Wearable", "keywords": ["smartwatch", "watch", "fitness band", "tracker"]},
    {"type": "Laptop / Computer",     "keywords": ["laptop", "notebook", "computer"]},
    {"type": "Bag / Handbag",         "keywords": ["bag", "handbag", "purse", "tote", "backpack"]},
    {"type": "Wallet",                "keywords": ["wallet", "cardholder"]},
    {"type": "Belt",                  "keywords": ["belt"]},
    {"type": "Sunglasses",            "keywords": ["sunglass", "sunglasses", "shades", "uv400"]},
    {"type": "Mouse / Peripheral",    "keywords": ["mouse", "keyboard"]},
]

WINTER_WORDS = ["winter", "warm", "heavy", "thermal", "insulated", "cold weather"]
SUMMER_WORDS = ["summer", "cool", "beach", "lightweight", "hot weather", "poolside"]

# ── Signal extractor ──────────────────────────────────────────────────────────

def extract_signals(p):
    title       = p.get("title", "").strip()
    desc        = p.get("descriptionPlain", "").strip()
    tags        = p.get("tags", [])
    category    = p.get("category") or {}
    wc          = p.get("descriptionWordCount", 0)
    image_count = p.get("imageCount", 0)

    has_specs    = bool(re.search(r'\b\d+\s*(gb|mb|w|kg|g|mm|mah|v|hours?)\b', desc, re.I))
    has_material = bool(re.search(r'\b(cotton|leather|polyester|silk|wool|nylon|canvas|rubber)\b', desc, re.I))
    has_usecase  = bool(re.search(r'\b(ideal for|perfect for|suitable for|designed for|best for)\b', desc, re.I))

    return {
        "title":       {"quality": "strong" if len(title) >= 10 else ("weak" if title else "absent")},
        "description": {
            "quality":      "strong" if wc >= 50 else "moderate" if wc >= 20 else "weak" if wc > 0 else "absent",
            "has_specs":    has_specs,
            "has_material": has_material,
            "has_usecase":  has_usecase,
        },
        "tags":    {"quality": "strong" if len(tags) >= 4 else ("weak" if tags else "absent"), "count": len(tags)},
        "images":  {"quality": "strong" if image_count >= 2 else ("moderate" if image_count == 1 else "absent")},
        "vendor":  {"quality": "present" if p.get("vendor", "").strip() else "absent"},
    }

# ── Type classifier ───────────────────────────────────────────────────────────

def classify_type(p):
    corpus = " ".join([
        p.get("title", ""),
        p.get("descriptionPlain", ""),
        " ".join(p.get("tags", [])),
        p.get("productType", "") or "",
    ]).lower()

    scores = []
    for entry in TYPE_VOCABULARY:
        matches = [kw for kw in entry["keywords"] if kw in corpus]
        if matches:
            scores.append({"type": entry["type"], "matches": matches, "score": len(matches)})

    scores.sort(key=lambda x: -x["score"])

    if not scores:
        return {"detected": "Unknown", "confidence": 0, "ambiguous": False, "alternatives": [], "matched_keywords": []}

    top    = scores[0]
    runner = scores[1] if len(scores) > 1 else None

    confidence = 0.9 if top["score"] >= 3 else 0.7 if top["score"] == 2 else 0.45
    ambiguous  = bool(runner and runner["score"] >= top["score"] * 0.75)

    return {
        "detected":          top["type"],
        "confidence":        confidence,
        "ambiguous":         ambiguous,
        "alternatives":      [runner["type"]] if runner else [],
        "matched_keywords":  top["matches"],
    }

# ── Retrieval scorer ──────────────────────────────────────────────────────────

def score_retrieval(signals):
    score = 0
    score += 30 if signals["title"]["quality"] == "strong"       else 10 if signals["title"]["quality"] == "weak" else 0
    score += 20 if signals["tags"]["quality"] == "strong"        else 8  if signals["tags"]["quality"] == "weak"  else 0
    score += 15 if signals["description"]["quality"] == "strong" else 8  if signals["description"]["quality"] == "moderate" else 3 if signals["description"]["quality"] == "weak" else 0
    score += 5  if signals["description"]["has_specs"]    else 0
    score += 5  if signals["description"]["has_material"] else 0
    score += 5  if signals["description"]["has_usecase"]  else 0
    score += 10 if signals["images"]["quality"] != "absent" else 0
    return min(100, score)

# ── Ambiguity detector ────────────────────────────────────────────────────────

def detect_ambiguity(p, type_result, signals):
    flags = []
    text = (p.get("title", "") + " " + p.get("descriptionPlain", "")).lower()

    if type_result["ambiguous"]:
        flags.append({
            "type": "TYPE_AMBIGUITY",
            "description": f"AI cannot distinguish between '{type_result['detected']}' and '{type_result['alternatives'][0]}'. Both plausible from text."
        })

    if type_result["confidence"] < 0.5:
        flags.append({
            "type": "LOW_CLASSIFICATION_CONFIDENCE",
            "description": f"Only {int(type_result['confidence']*100)}% confidence in product type. Insufficient signals."
        })

    if signals["description"]["quality"] == "absent" and signals["tags"]["quality"] == "absent":
        flags.append({
            "type": "CONTEXT_VACUUM",
            "description": "No description and no tags. AI relies entirely on title — extreme ambiguity risk."
        })

    has_winter = any(w in text for w in WINTER_WORDS)
    has_summer = any(w in text for w in SUMMER_WORDS)
    if has_winter and has_summer:
        flags.append({
            "type": "CONTRADICTORY_CONTEXT",
            "description": "Conflicting seasonal signals. AI may filter this out of both winter AND summer queries."
        })

    return flags

# ── Missing signals ───────────────────────────────────────────────────────────

def detect_missing_signals(p, signals, type_result):
    missing = []

    if signals["title"]["quality"] == "absent":
        missing.append({"signal": "title", "impact": "CRITICAL", "reason": "No title = no AI classification entry point."})
    if signals["tags"]["quality"] == "absent":
        missing.append({"signal": "tags", "impact": "HIGH", "reason": "No tags = invisible to keyword-based AI retrieval."})
    if signals["description"]["quality"] == "absent":
        missing.append({"signal": "description", "impact": "HIGH", "reason": "No description = AI has no context for disambiguation."})
    if signals["images"]["quality"] == "absent":
        missing.append({"signal": "images", "impact": "HIGH", "reason": "No images = vision AI agents cannot verify product."})
    if not signals["description"]["has_specs"] and "Laptop" in type_result["detected"]:
        missing.append({"signal": "specs", "impact": "HIGH", "reason": "Electronics without specs cannot rank in comparison queries."})
    if not signals["description"]["has_material"] and type_result["detected"] in ["T-Shirt / Top", "Jacket / Outerwear", "Footwear"]:
        missing.append({"signal": "material", "impact": "MEDIUM", "reason": "Apparel without material misses 'cotton shirts' type queries."})
    if not signals["description"]["has_usecase"]:
        missing.append({"signal": "use_case", "impact": "LOW", "reason": "No use-case context = cannot match intent queries like 'office wear'."})

    return missing

# ── Perception builder ────────────────────────────────────────────────────────

def generate_perception(product):
    signals       = extract_signals(product)
    type_result   = classify_type(product)
    retrieval     = score_retrieval(signals)
    ambiguity     = detect_ambiguity(product, type_result, signals)
    missing       = detect_missing_signals(product, signals, type_result)

    retrieval_grade = (
        "HIGH — Will appear in relevant AI searches"        if retrieval >= 75 else
        "MEDIUM — May appear depending on query phrasing"   if retrieval >= 50 else
        "LOW — Unlikely to surface in most AI searches"     if retrieval >= 25 else
        "VERY LOW — Near-invisible to AI retrieval systems"
    )

    parts = []
    if type_result["detected"] != "Unknown" and type_result["confidence"] >= 0.7:
        parts.append(f"AI classifies this as '{type_result['detected']}' with {int(type_result['confidence']*100)}% confidence.")
    elif type_result["detected"] != "Unknown":
        parts.append(f"AI tentatively sees '{type_result['detected']}' but confidence is low ({int(type_result['confidence']*100)}%).")
    else:
        parts.append("AI cannot determine product type from available signals.")

    if ambiguity:
        parts.append(f"{len(ambiguity)} ambiguity issue(s) detected.")
    else:
        parts.append("No conflicting signals.")

    desc_q = signals["description"]["quality"]
    if desc_q == "strong":      parts.append("Description provides strong context.")
    elif desc_q in ("weak","moderate"): parts.append("Description present but too thin for attribute extraction.")
    else:                       parts.append("No description — AI operating blind on context.")

    return {
        "handle":  product["handle"],
        "title":   product["title"],
        "aiPerception": {
            "perceivedType":    type_result["detected"],
            "typeConfidence":   int(type_result["confidence"] * 100),
            "isAmbiguous":      len(ambiguity) > 0,
            "retrievalScore":   retrieval,
            "retrievalGrade":   retrieval_grade,
            "interpretation":   " ".join(parts),
            "ambiguityFlags":   ambiguity,
            "missingSignals":   missing,
            "signalStrengths":  {k: v["quality"] for k, v in signals.items()},
        }
    }

# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    with open("data/products.json", encoding="utf-8") as f:
        products_data = json.load(f)

    print(f"[ai_perception] Processing {len(products_data['products'])} products...")

    perceptions = [generate_perception(p) for p in products_data["products"]]

    avg_retrieval = sum(p["aiPerception"]["retrievalScore"] for p in perceptions) / len(perceptions)

    output = {
        "meta": {
            "generatedAt":       datetime.now().isoformat(),
            "productsProcessed": len(perceptions),
            "avgRetrievalScore": round(avg_retrieval, 1),
            "storeVisibility":   "HIGH" if avg_retrieval >= 75 else "MEDIUM" if avg_retrieval >= 50 else "LOW" if avg_retrieval >= 25 else "CRITICAL",
        },
        "summary": {
            "typeDistribution":    {},
            "ambiguousProducts":   sum(1 for p in perceptions if p["aiPerception"]["isAmbiguous"]),
            "highRetrieval":       sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] >= 75),
            "lowRetrieval":        sum(1 for p in perceptions if p["aiPerception"]["retrievalScore"] < 40),
        },
        "perceptions": perceptions,
    }

    for p in perceptions:
        t = p["aiPerception"]["perceivedType"]
        output["summary"]["typeDistribution"][t] = output["summary"]["typeDistribution"].get(t, 0) + 1

    with open("data/perception.json", "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n{'='*50}")
    print(f"  AI PERCEPTION REPORT")
    print(f"{'='*50}")
    print(f"  Avg retrieval score : {avg_retrieval:.1f}/100")
    print(f"  Store visibility    : {output['meta']['storeVisibility']}")
    print(f"  Ambiguous products  : {output['summary']['ambiguousProducts']}")
    print(f"  High retrieval      : {output['summary']['highRetrieval']} products")
    print(f"  Low retrieval       : {output['summary']['lowRetrieval']} products")
    print(f"\n  Type distribution:")
    for t, count in sorted(output["summary"]["typeDistribution"].items(), key=lambda x: -x[1]):
        print(f"    {t:<30} {count} products")
    print(f"{'='*50}")
    print(f"\n[ai_perception] Saved to data/perception.json")