# Technical Architecture & Documentation

## 1. System Overview
The AI Representation Optimizer is built as a modular Python pipeline that operates in distinct stages: Fetching, Policy Checks, Trust Analysis, Product Analysis, AI Perception Simulation, and Reporting. 

The entire system is glued together by `src/main.py`, utilizing local JSON file storage (`/data`) as a temporary fast-access database, and serving a frontend dashboard via Flask.

## 2. Technology Stack
- **Language:** Python 3.10+
- **APIs:** 
  - Shopify Admin API (GraphQL & REST)
  - Google Gemini API (`gemini-2.5-flash`)
- **Backend/Dashboard:** Flask
- **Frontend UI:** HTML5, Vanilla CSS, Vanilla JavaScript (Dynamic polling)

## 3. Core Modules

### 3.1 `src/fetcher.py` (Data Ingestion)
- **Mechanism:** Executes a robust GraphQL query against the Shopify Admin API.
- **Data Extracted:** Standard fields (title, vendor, tags), rich HTML descriptions, Image data with ALT text, pricing, SEO metadata, and Taxonomy Categories.
- **Output:** Normalizes data into a simplified Python dictionary and saves to `data/products.json`.

### 3.2 `src/checks/faq_policy.py` & `src/checks/trust_signals.py`
- **Policy Checker:** Scans the Shopify store's Pages and Policies (`/policies.json`). It uses regex and keyword heuristics to identify missing policies, thin content, and missing delivery timeframes.
- **Trust Signals:** Iterates over the fetched catalog to evaluate brand consistency (number of unique vendors), social proof keywords, and secure checkout mentions.

### 3.3 `src/analyzer.py` (Heuristic Engine)
- **Mechanism:** A rule-based engine that processes each product through 23 discrete checks.
- **Configuration:** Pulls severity weights, rule toggles, and vocabulary lists (e.g., vague words, material words) from `src/rules_config.json`. This allows for non-code updates to the scoring logic.
- **Scoring System:** Calculates a `Product Score` (0-100) and integrates Trust/Policy data to compute a final `Composite Score` (60% Product / 20% Policy / 20% Trust).

### 3.4 `src/ai_perception.py` (LLM Simulation)
- **Mechanism:** Constructs a focused prompt containing the product's title, type, and plain-text description.
- **Inference:** Calls Gemini to ask for a JSON response containing an inferred product type, a confidence percentage, an ambiguity boolean, and an estimated retrieval score.
- **Caching:** Saves perception data so it does not need to be re-run unnecessarily, reducing API costs.

### 3.5 `src/reporter/app.py` (Flask Dashboard)
- **Mechanism:** Serves an HTML dashboard (`templates/index.html`).
- **Endpoints:** 
  - `/api/stats`: Serves aggregated health data, scores, and the executive summary.
  - `/api/issues/top`: Serves the ranked ROI Fix list.
  - `/api/products`: Serves the filterable product grid.
  - `/api/rescore/<handle>`: Allows real-time re-triggering of the pipeline for a single product to reflect live updates.

## 4. Configuration (`rules_config.json`)
The `rules_config.json` file is central to the application's flexibility. It dictates:
1. **Rule Enablement:** Turn individual rules on/off.
2. **Severities:** Assign CRITICAL, HIGH, MEDIUM, LOW impact to rules.
3. **Thresholds:** Configurable length limits for descriptions and titles.
4. **Vocabularies:** Lists of words that trigger warnings (e.g., "best", "cheap", "amazing") vs. words that add value (e.g., "cotton", "leather", "usb-c").

## 5. Future Scalability Considerations
- **Database:** Replace the ephemeral `data/*.json` files with SQLite or PostgreSQL to handle catalogs exceeding 1,000 products efficiently.
- **Rate Limiting:** Implement Shopify GraphQL cursor pagination and leaky-bucket rate-limit handling for large data extraction.
- **Webhooks:** Transition from manual polling/fetching to Shopify Webhooks (e.g., `products/update`) to automatically trigger re-scores when a merchant edits a product in Shopify.
