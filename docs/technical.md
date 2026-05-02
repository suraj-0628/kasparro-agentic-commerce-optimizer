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

### 3.5 `src/llm_enhancer.py` (The Remediation Engine)
- **Mechanism:** Acts as the "Writer" for the system. When a fix is requested, it constructs a complex prompt including current product data + 23 rule violations.
- **Inference:** Uses high-reasoning models (Llama-3-70B via Groq or GPT-4o) to generate a "Perfect AI Representation."
- **Shopify Sync:** Directly interfaces with the Shopify GraphQL API to update the live product record, including variant-level SKU generation.

### 3.6 `src/checks/query_simulator.py` (AI Search Benchmarking)
- **Mechanism:** Simulates how an AI agent (like Perplexity) retrieves products.
- **Dynamic Loader:** Loads a store-specific "Market Simulation" from `data/auto_queries.json`.
- **Match Logic:** Implements a "Category-Aware Match Engine" that evaluates Category Gatekeeping, Required Keyword Signals, and Synonym mapping.
- **Output:** Returns a "Match Count" (e.g., 3/15 queries) providing a tangible discoverability metric.

### 3.7 `src/reporter/app.py` (Fast-Sync Architecture)
- **Mechanism:** Serves an HTML dashboard (`templates/index.html`).
- **Real-Time Pipeline:** Implements a cache-busting logic in the `/product/<handle>` route that forces a live re-analysis and query simulation every time the page is loaded, ensuring the dashboard reflects the very latest Shopify data.
- **API Endpoints:** 
  - `/api/apply/<handle>`: Triggers the LLM Enhancer and Shopify Sync.
  - `/api/rescore/<handle>`: Forces a fast-track analysis and simulation run.
  - `/api/stats`: Aggregates store-wide ROI and health data.

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
