# AI Representation Optimizer

AI Representation Optimizer is a tool that analyzes Shopify stores to determine how visible and understandable their products and brand are to next-generation AI shopping agents (like ChatGPT, Claude, and Gemini).

Unlike traditional SEO tools which focus on Google keyword ranking, this optimizer focuses on **LLM Retrieval Optimization (LRO)** by ensuring products have deep contextual metadata, zero ambiguity, and strong trust signals (like clear policies and social proof) so AI agents confidently recommend them to users.

---

## 🚀 Features

### Product Quality Analysis
Checks for 20+ signals including:
- Missing images
- Vague descriptions
- Missing categories
- Short titles
- Product contradictions

### Store-Level Trust Signals
Automatically checks for:
- Branding consistency
- Social proof
- Secure checkout guarantees
- Industry certifications

### Automated Policy & FAQ Audit
Scans your store to verify:
- Return/Refund policies
- Shipping policies
- Privacy policies
- FAQ pages

### AI Perception Simulation
Uses Gemini to simulate how an AI shopping agent perceives a product by:
- Scoring retrieval likelihood
- Detecting semantic ambiguity
- Identifying missing trust/context signals

### Composite Store Scoring
Generates a unified Store Health Score based on:
- Product Quality → 60%
- Policy Health → 20%
- Trust Signals → 20%

### High-ROI Action Plan
Ranks all detected issues by:
- Estimated fix impact
- Score improvement potential
- Number of affected products

### Modern Dashboard UI
Provides:
- Executive summaries
- Health metrics
- Dynamic fix recommendations
- Product-level insights

---

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