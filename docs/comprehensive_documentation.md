# AI Representation Optimizer — Product & Technical Documentation

## 1. Product Overview

### Objective
The **AI Representation Optimizer** is a specialized e-commerce tool designed to audit, score, and automatically optimize Shopify product listings specifically for **AI Shopping Agents** (such as Google Shopping algorithms, Bing, ChatGPT shopping extensions, and other LLM-based discovery tools).

### Core Value Proposition
Traditional SEO tools optimize for human readers and standard search engines. This application optimizes for the *signal density* required by AI classifiers. It provides:
1. **Automated Auditing**: Instantly scans an entire Shopify catalog and grades products on their "AI Visibility".
2. **AI Simulation**: Mimics how an LLM would interpret a product, flagging ambiguity or conflicting signals (e.g., a "Winter" jacket that mentions "Beach").
3. **One-Click Fixes**: Uses Generative AI to rewrite descriptions, titles, and SEO metadata to perfectly align with what AI retrieval systems look for.
4. **Real-Time Sync**: Pushes approved changes directly to the live Shopify store via API.

---

## 2. High-Level Architecture

The system is built as a hybrid CLI pipeline and local Web Dashboard.

*   **Backend / Processing**: Python 3.x
*   **Web Framework**: Flask (Development Server)
*   **Frontend**: Vanilla HTML / CSS / JavaScript (Jinja2 Templating)
*   **External APIs**: 
    *   Shopify Admin GraphQL API
    *   Google Gemini API (Primary LLM)
    *   OpenAI API (Fallback LLM)
*   **Data Storage**: Local JSON flat files (`data/products.json`, `data/report.json`, etc.) functioning as an ephemeral cache/database.

---

## 3. Minute Component Details

### A. Data Fetching (`src/fetcher.py`)
*   **Mechanism**: Uses Shopify's GraphQL API to fetch product nodes including `title`, `descriptionHtml`, `tags`, `seo`, and `images`.
*   **Data Cleaning**: Strips HTML tags from `descriptionHtml` using regular expressions to create a `descriptionPlain` field, which is critical for accurate word counting and NLP analysis.

### B. Quality Analyzer (`src/analyzer.py`)
The core rule engine that evaluates products against 17 distinct heuristics:
*   **CRITICAL (30 pt deduction)**: Missing titles, missing descriptions.
*   **HIGH (15 pt deduction)**: Missing tags, missing images, titles under 10 chars, descriptions under 20 words, vague descriptions, contradictory seasonal keywords.
*   **MEDIUM (8 pt deduction)**: Missing material (for apparel), missing specs (for electronics), spammy ALL-CAPS usage.
*   **LOW (3 pt deduction)**: Missing SEO metadata, missing vendor/brand information, missing image alt text.
*   **Output**: Generates a 0-100 Quality Score and assigns a Grade (A, B, C, F).

### C. AI Perception Engine (`src/ai_perception.py`)
Simulates how an external AI agent views the product.
*   **Retrieval Scoring**: Scores the likelihood of a product surfacing in an AI search based on "signal strength" (e.g., strong tags = +20, strong description = +15).
*   **Type Classifier**: Uses a `TYPE_VOCABULARY` dictionary and whole-word Regex boundary matching (`\bkeyword(?:s|es)?\b`) to assign the product to a taxonomy (e.g., "Laptop / Computer", "T-Shirt / Top").
*   **Confidence Calculation**: Dynamically scales the classification confidence (0% to 98%) based on keyword matches multiplied by the signal quality of the title, description, and tags.
*   **Ambiguity Detection**: Flags products if they tie between multiple categories, or if they have contradictory signals.

### D. Recommender Engine (`src/recommender.py`)
Translates the raw rule failures from the Analyzer into actionable tasks.
*   Sorts issues by Priority and Effort (LOW, MEDIUM, HIGH).
*   Identifies "Quick Wins" (High/Critical severity issues that require Low effort).
*   Aggregates data to generate **Store-Level Insights**, highlighting systemic issues (e.g., "30/30 products are missing SEO metadata").

### E. LLM Enhancer (`src/llm_enhancer.py`)
Handles all Generative AI interactions.
*   **Dual-Provider Support**: Attempts to use Google Gemini first. If quota limits are reached, gracefully falls back to OpenAI (if configured).
*   **Resilience**: Implements automatic exponential backoff retry logic to handle `503 Service Unavailable` and `429 Too Many Requests` spikes from the LLM providers.
*   **Prompt Engineering**: Uses highly structured system prompts enforcing strict JSON output schemas, ensuring the response can be directly parsed and injected into the frontend without formatting errors.

### F. Image Validation & Uploads (`src/image_handler.py`)
*   **Validation**: Uses PIL (Python Imaging Library) to check dimensions and aspect ratios.
*   **OCR Integration**: Uses Tesseract OCR to detect if an image contains too much overlay text (a spam signal for AI shopping agents).
*   **Uploads**: Converts files to base64 or multipart form data to upload directly to Shopify's `stagedUploadsCreate` GraphQL endpoints.

### G. Shopify Writer (`src/shopify_writer.py`)
*   Executes GraphQL `productUpdate` mutations to safely push the AI-generated changes back to the live store.
*   Updates Title, Body HTML, Tags, and SEO Metafields in real-time.

### H. Dashboard UI (`src/reporter/app.py` & `templates/`)
*   **Flask Routes**: Serves the UI and acts as a REST API for frontend interactions.
*   **Dynamic Data Binding**: The `product.html` template features a "Generate AI Improvements" modal.
*   **Auto-Sync Architecture**: When a user clicks "Apply to Shopify", the JavaScript:
    1. Sends the changes to `api_apply`.
    2. Waits 2 seconds for Shopify's cache to flush.
    3. Calls `api_rerun` to pull fresh data and recalculate all scores (Analyzer + Perception).
    4. Automatically reloads the page to dynamically display the new 100/100 score to the user.

---

## 4. End-to-End Workflow: The "One-Click Fix"

1. **Discovery**: User views the Dashboard and sees a product with a Grade F (Score: 30/100).
2. **Analysis**: User clicks into the product. The UI clearly states *why* the AI struggles to understand the product (e.g., "Missing Material", "Title too short").
3. **Generation**: User clicks "Generate AI Improvements". `llm_enhancer.py` crafts a new Title, SEO Description, and plain Description.
4. **Review**: The new text appears in a modal for the user to review.
5. **Execution**: User clicks "Apply to Shopify". `shopify_writer.py` pushes the update.
6. **Re-Evaluation**: The system automatically triggers the pipeline. The new text is analyzed. The AI Perception Engine sees strong new signals and upgrades the classification confidence to 98%.
7. **Success**: The UI reloads, showing a Grade A, 100/100 score, and a "HIGH" retrieval visibility grade.
