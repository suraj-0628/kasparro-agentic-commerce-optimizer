AI Representation Optimizer
AI Representation Optimizer is a tool that analyzes Shopify stores to determine how visible and understandable their products and brand are to next-generation AI shopping agents (like ChatGPT, Claude, and Gemini).
Unlike traditional SEO tools which focus on Google keyword ranking, this optimizer focuses on LLM Retrieval Optimization (LRO) by ensuring products have deep contextual metadata, zero ambiguity, and strong trust signals (like clear policies and social proof) so AI agents confidently recommend them to users.
---
🚀 Features
Product Quality Analysis: Checks for 20+ signals including missing images, vague descriptions, missing categories, short titles, and contradictions.
Store-Level Trust Signals: Automatically checks for consistency in branding, social proof, secure checkout guarantees, and industry certifications.
Automated Policy & FAQ Audit: Scans your store to verify the existence and quality of Return/Refund policies, Shipping policies, Privacy policies, and FAQ pages.
AI Perception Simulation: Uses Gemini to simulate how an AI shopping agent actually perceives a product. It scores the retrieval likelihood and identifies any semantic ambiguity.
Composite Store Scoring: Generates a unified Store Health Score based on Product Quality (60%), Policy Health (20%), and Trust Signals (20%).
High-ROI Action Plan: Automatically ranks all issues by their "fix impact," showing you exactly which issues to solve first to get the highest score boost across the most products.
Modern Dashboard UI: A sleek Flask web dashboard displaying executive summaries, health metrics, and a dynamic fix table.
---
🛠️ Setup Instructions
1. Prerequisites
Python 3.10+
Git
A custom Shopify app setup to get an Admin API Access Token (GraphQL read access required).
2. Clone the Repository
```bash
git clone <your-repository-url>
cd kas_antigravity
```
3. Create & Activate Virtual Environment (Windows PowerShell)
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
(On macOS/Linux, use `source .venv/bin/activate`)
4. Install Dependencies
```powershell
pip install -r requirements.txt
```
5. Environment Variables
Create a `.env` file in the root directory (where `src` is located) and add your keys:
```env
SHOPIFY_STORE=your-store-name
SHOPIFY_TOKEN=shpat_your_shopify_admin_access_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```
(Note: Use your Shopify store's handle, e.g., if your URL is `my-store.myshopify.com`, use `my-store` for SHOPIFY_STORE).
---
🏃‍♂️ Running the Optimizer
1. Run the Full CLI Pipeline
To fetch the latest store data, run the AI audits, and generate the JSON reports:
```powershell
python src/main.py
```
This process takes a few seconds and will save all analysis to the `data/` folder.
2. Launch the Web Dashboard
To view your results visually in the local Flask application:
```powershell
python src/main.py --serve
```
Then open your browser and navigate to: http://127.0.0.1:5000
---
📂 Project Structure
```
.
├── src/
│   ├── main.py               # Main CLI entry point
│   ├── fetcher.py            # Shopify GraphQL data fetcher
│   ├── analyzer.py           # Core heuristic scoring engine
│   ├── ai_perception.py      # Gemini-powered LLM perception simulation
│   ├── rules_config.json     # Configuration for weights, vocab, and strictness
│   ├── checks/               # Store-wide checks (Trust & Policy)
│   │   ├── trust_signals.py
│   │   └── faq_policy.py
│   └── reporter/             # Flask Dashboard
│       ├── app.py            
│       └── templates/
│           └── index.html    # Dashboard UI
├── data/                     # Output directory for JSON reports (ephemeral)
├── docs/                     # Documentation (Product & Technical specs)
├── .env                      # Environment variables
└── requirements.txt          # Python dependencies
```
