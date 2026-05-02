import os
import json

# ── Static Fallback Database ──────────────────────────────────────────────────
# These are used if no dynamic queries are generated.
QUERY_DATABASE = [
    {
        "query":      "ayurvedic face cream for dry skin India",
        "category":   "skincare",
        "intent":     "purchase",
        "required":   ["ayurvedic", "cream", "dry"],
        "signals":    ["formulation", "category", "skin_type"],
    },
    {
        "query":      "SPF 50 sunscreen for Indian summer",
        "category":   "skincare",
        "intent":     "purchase",
        "required":   ["spf", "sunscreen"],
        "signals":    ["spec", "category", "season"],
    },
    {
        "query":      "vitamin C serum for brightening under 500",
        "category":   "skincare",
        "intent":     "purchase",
        "required":   ["vitamin c", "serum"],
        "priceMax":   500,
        "signals":    ["ingredient", "category", "price"],
    },
    {
        "query":      "running shoes under 2000 for gym India",
        "category":   "footwear",
        "intent":     "purchase",
        "required":   ["running", "shoe", "gym"],
        "priceMax":   2000,
        "signals":    ["activity", "price", "category"],
    },
    {
        "query":      "comfortable canvas sneakers for daily use",
        "category":   "footwear",
        "intent":     "purchase",
        "required":   ["canvas", "sneaker", "daily"],
        "signals":    ["material", "use_case", "category"],
    },
    {
        "query":      "formal leather shoes for office wear men",
        "category":   "footwear",
        "intent":     "purchase",
        "required":   ["formal", "leather", "shoe", "office"],
        "signals":    ["occasion", "material", "category"],
    },
    {
        "query":      "warm jacket for Delhi winter",
        "category":   "apparel",
        "intent":     "purchase",
        "required":   ["jacket", "winter", "warm"],
        "signals":    ["category", "season", "benefit"],
    },
    {
        "query":      "cotton kurta for office wear under 1000 rupees",
        "category":   "apparel",
        "intent":     "purchase",
        "required":   ["cotton", "kurta", "office"],
        "priceMax":   1000,
        "signals":    ["material", "category", "price"],
    },
    {
        "query":      "lightweight summer shirt for men India",
        "category":   "apparel",
        "intent":     "purchase",
        "required":   ["summer", "shirt", "men"],
        "signals":    ["season", "category", "gender"],
    },
    {
        "query":      "best cotton kurta for office wear under 1000 rupees",
        "category":   "apparel",
        "intent":     "purchase",
        "required":   ["cotton", "kurta"],
        "priceMax":   1000,
        "signals":    ["material", "category", "price"],
    },
    {
        "query":      "noise cancelling headphones for travel India",
        "category":   "electronics",
        "intent":     "purchase",
        "required":   ["noise", "cancelling", "headphone"],
        "signals":    ["feature", "category", "use_case"],
    },
    {
        "query":      "fast charger for Android phone 33W",
        "category":   "electronics",
        "intent":     "purchase",
        "required":   ["fast", "charger"],
        "signals":    ["spec", "category"],
    },
    {
        "query":      "smartwatch with heart rate monitor India",
        "category":   "electronics",
        "intent":     "purchase",
        "required":   ["smartwatch", "heart rate"],
        "signals":    ["spec", "feature", "category"],
    },
    # General / High Volume
    {
        "query":      "white sneakers for daily use comfortable",
        "category":   "footwear",
        "intent":     "purchase",
        "required":   ["white", "sneaker", "daily"],
        "signals":    ["color", "category", "use_case"],
    },
    {
        "query":      "premium leather shoes for men",
        "category":   "footwear",
        "intent":     "purchase",
        "required":   ["leather", "shoe"],
        "signals":    ["material", "category"],
    },
    {
        "query":      "winter hoodie with pockets warm",
        "category":   "apparel",
        "intent":     "purchase",
        "required":   ["hoodie", "winter", "warm"],
        "signals":    ["category", "season"],
    },
    {
        "query":      "long-lasting pink nail polish chip resistant",
        "category":   "skincare",
        "intent":     "purchase",
        "required":   ["nail polish", "pink"],
        "signals":    ["category", "color", "benefit"],
    },
    {
        "query":      "organic beauty products for daily makeup",
        "category":   "skincare",
        "intent":     "purchase",
        "required":   ["beauty", "cosmetic"],
        "signals":    ["formulation", "category"],
    },
]

# ── Dynamic Loader ────────────────────────────────────────────────────────────

def get_query_database():
    """Returns the dynamic query database, falling back to static if needed."""
    try:
        db_path = os.path.join("data", "auto_queries.json")
        if os.path.exists(db_path):
            with open(db_path, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[simulator] Error loading dynamic queries: {e}")
    return QUERY_DATABASE

# ── Match engine ──────────────────────────────────────────────────────────────

def product_matches_query(product: dict, query: dict) -> dict:
    """
    Checks if a product would surface for a given AI search query.
    """
    corpus = " ".join([
        product.get("title", ""),
        product.get("descriptionPlain", ""),
        " ".join(product.get("tags", [])),
        product.get("productType", "") or "",
        (product.get("category") or {}).get("fullName", ""),
    ]).lower()

    matched_signals  = []
    missing_signals  = []
    price_ok         = True

    # HARD CATEGORY GATE
    query_cat = query.get("category", "overall")
    product_type = (product.get("productType") or "").lower()
    product_tags = [t.lower() for t in product.get("tags", [])]
    
    # Mapping query categories to product types/tags
    cat_map = {
        "apparel":     ["shirt", "hoodie", "jacket", "kurta", "top", "pant", "clothing", "wear"],
        "footwear":    ["shoe", "sneaker", "sandal", "boot", "flip flop", "footwear"],
        "skincare":    ["cream", "serum", "lotion", "oil", "face wash", "beauty", "nail", "polish", "cosmetic", "skin", "makeup"],
        "electronics": ["headphone", "watch", "speaker", "laptop", "charger", "tech"],
        "accessories": ["belt", "bag", "wallet", "sunglass", "jewelry"]
    }
    
    # If the product doesn't belong in the query category, it's a 0% match immediately
    if query_cat in cat_map:
        is_in_cat = any(kw in product_type or kw in " ".join(product_tags) for kw in cat_map[query_cat])
        if not is_in_cat:
            # FALLBACK: If keywords are strong, ignore the category mismatch
            strong_keywords = sum(1 for kw in query.get("required", []) if kw.lower() in corpus)
            if strong_keywords < len(query.get("required", [])):
                return {
                    "query": query["query"],
                    "wouldSurface": False,
                    "matchScore": 0.0,
                    "matchedSignals": [],
                    "missingSignals": ["category_mismatch"],
                    "priceCompatible": True,
                    "descriptionThin": False,
                    "intent": query["intent"],
                }

    # Check required keywords
    for keyword in query.get("required", []):
        if keyword.lower() in corpus:
            matched_signals.append(keyword)
        else:
            missing_signals.append(keyword)

    if matched_signals:
        print(f"[simulator] Product '{product.get('handle')}' matched {len(matched_signals)} signals for query '{query['query']}'")

    # Check price
    price_max = query.get("priceMax")
    if price_max and product.get("price", 0) > price_max:
        price_ok = False
        missing_signals.append(f"price > ₹{price_max}")

    # Matching logic
    desc_wc = product.get("descriptionWordCount", 0)
    desc_penalized = desc_wc < 10
    total_required = len(query.get("required", []))
    matched_count  = len(matched_signals)

    match_score = matched_count / total_required if total_required > 0 else 0
    
    # Fuzzy synonyms
    if match_score < 1.0:
        synonyms = {"hoodie": "jacket", "shirt": "top", "sneaker": "shoe", "cream": "lotion"}
        for missing in missing_signals:
            if missing.lower() in synonyms:
                if synonyms[missing.lower()] in corpus:
                    match_score += (0.2 / total_required)
    
    if desc_penalized: match_score *= 0.7
    
    has_img = product.get("hasImages") or len(product.get("images", [])) > 0
    if not has_img: match_score *= 0.8

    would_surface = match_score >= 0.5

    return {
        "query":           query["query"],
        "wouldSurface":    would_surface,
        "matchScore":      round(match_score, 2),
        "matchedSignals":  matched_signals,
        "missingSignals":  missing_signals,
        "priceCompatible": price_ok,
        "descriptionThin": desc_penalized,
        "intent":          query["intent"],
    }

# ── Store-level simulation ───────────────────────────────────────────────────

def simulate_queries(products: list) -> dict:
    db = get_query_database()
    results = []
    zero_match_queries = []
    total_queries = len(db)

    for query in db:
        matches = []
        for product in products:
            match = product_matches_query(product, query)
            if match["wouldSurface"]:
                matches.append({"handle": product["handle"], "title": product["title"]})
        
        results.append({
            "query":   query["query"],
            "count":   len(matches),
            "matches": matches[:5],
            "intent":  query["intent"]
        })
        if not matches:
            zero_match_queries.append(query["query"])
    
    product_coverage = {}
    for p in products:
        p_matches = 0
        p_results = []
        for q in db:
            m = product_matches_query(p, q)
            if m["wouldSurface"]:
                p_matches += 1
                p_results.append(m)
        
        product_coverage[p["handle"]] = {
            "queriesMatched": p_matches,
            "visibilityRate": round((p_matches / total_queries) * 100) if total_queries > 0 else 0,
            "matches":        p_results
        }

    return {
        "totalQueries":      total_queries,
        "coverageRate":      round((len(results) - len(zero_match_queries)) / total_queries * 100) if total_queries > 0 else 0,
        "zeroMatchQueries":  zero_match_queries,
        "productCoverage":   product_coverage,
        "allResults":        results
    }