# AI Representation Optimizer

AI Representation Optimizer is a tool that analyzes Shopify stores to determine how visible and understandable their products and brand are to next-generation AI shopping agents (like ChatGPT, Claude, and Gemini).

Unlike traditional SEO tools which focus on Google keyword ranking, this optimizer focuses on **LLM Retrieval Optimization (LRO)** by ensuring products have deep contextual metadata, zero ambiguity, and strong trust signals (like clear policies and social proof) so AI agents confidently recommend them to users.

---

## 📺 Demo Video
[Watch Walkthrough ](YOUR_YOUTUBE_LINK_HERE)

---

## 🚀 Features

### ✦ One-Click Full AI Repair (Remediation)
Moving beyond analysis into instant action.
- **Atomic Optimization**: Automatically generates Grade A Titles, Descriptions, and Tags using high-reasoning LLMs.
- **Direct Shopify Sync**: Pushes improvements to the live store via GraphQL API with a single click.
- **Instant Rescore**: Fast-track re-analysis to show immediate score improvement.

### AI Search Visibility (Simulation)
- **Dynamic Market Queries**: Simulates real-world shopper queries (e.g., "warm hoodie for winter").
- **Intent Matching**: Category-aware engine that evaluates how well your product surfaces for AI agents like Perplexity or ChatGPT.

### Product Quality Analysis
Checks for 23+ signals including:
- Missing images & ALT text
- Vague descriptions (semantic thinness)
- Missing categories & SKUs
- Product-metadata contradictions
...and more.

### Store-Level Trust & Policy Audit
- **Policy Health**: Scans for Shipping, Returns, and Privacy compliance.
- **Trust Signals**: Evaluates social proof, branding consistency, and industry certifications.

### Composite Store Scoring & ROI
- **Industry Benchmarking**: Compare your store against the 95th percentile of AI-optimized stores.
- **ROI-First Priority**: Ranks fixes by **Total Point Lift**, showing you exactly what to fix to see the biggest jump in store health.

---
<img width="1876" height="868" alt="image" src="https://github.com/user-attachments/assets/fd1bf747-776c-4e74-8083-57665c37156e" />


## 🛠️ Setup Instructions

### 1. Prerequisites

Make sure you have the following installed:

- Python 3.10+
- Git
- Shopify Admin API Access Token
- Gemini API Key

---

### 2. Clone the Repository

```bash
git clone <your-repository-url>
cd kasparro-agentic-commerce-optimizer
```

---

### 3. Create & Activate Virtual Environment

#### Windows PowerShell

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### macOS/Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

### 4. Install Dependencies

```bash
pip install -r requirements.txt
```

---

### 5. Configure Environment Variables

Create a `.env` file in the project root directory and add:

```env
SHOPIFY_STORE=your-store-name
SHOPIFY_TOKEN=shpat_your_shopify_admin_access_token_here
GEMINI_API_KEY=your_gemini_api_key_here
```

### Example

If your Shopify store URL is:

```text
my-store.myshopify.com
```

Then use:

```env
SHOPIFY_STORE=my-store
```

---

## 🏃 Running the Optimizer

### Run Full CLI Pipeline

This command:
- Fetches Shopify store data
- Runs AI audits
- Generates JSON reports

```bash
python src/main.py
```

Generated reports will be saved inside the `data/` folder.

---

### Launch Web Dashboard

```bash
python src/main.py --serve
```

Open your browser and visit:

```text
http://127.0.0.1:5000
```

---

## 📂 Project Structure

```text
.
├── src/
│   ├── main.py               # Main CLI entry point
│   ├── fetcher.py            # Shopify GraphQL data fetcher
│   ├── analyzer.py           # Core heuristic scoring engine
│   ├── ai_perception.py      # Gemini-powered LLM perception simulation
│   ├── rules_config.json     # Weights, vocab, and scoring config
│   │
│   ├── checks/
│   │   ├── trust_signals.py  # Trust signal analysis
│   │   └── faq_policy.py     # FAQ and policy validation
│   │
│   └── reporter/
│       ├── app.py            # Flask application
│       └── templates/
│           └── index.html    # Dashboard UI
│
├── data/                     # Generated analysis reports
├── docs/                     # Documentation
├── .env                      # Environment variables
├── requirements.txt          # Python dependencies
└── README.md
```

---

## 📊 Scoring Methodology

The optimizer evaluates stores using three major dimensions:

| Category | Weight |
|----------|--------|
| Product Quality | 60% |
| Policy Health | 20% |
| Trust Signals | 20% |

Each product and store is analyzed to determine:
- AI discoverability
- Semantic clarity
- Trustworthiness
- Retrieval confidence

---

## 🤖 Tech Stack

### Backend
- Python
- Flask
- Shopify GraphQL API

### AI & Analysis
- Gemini API
- Heuristic Scoring Engine
- LLM Retrieval Optimization (LRO)

### Frontend
- HTML
- CSS
- Bootstrap (optional)

---

## 📌 Use Cases

- Improve AI discoverability for Shopify stores
- Optimize products for AI shopping assistants
- Increase semantic clarity for LLM retrieval
- Detect trust and policy gaps
- Improve product metadata quality

---

## 🔮 Future Improvements

- Multi-store benchmarking
- Competitor comparison
- AI-generated metadata suggestions
- Real-time Shopify sync
- Vector search integration
- Product embedding analysis

---

## 🤝 Contributors

- Suraj
- Pavalasri

---

## 📄 License

This project is developed for educational and research purposes.

---
