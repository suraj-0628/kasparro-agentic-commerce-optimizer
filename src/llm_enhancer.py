"""
src/llm_enhancer.py
REPLACE EXISTING FILE

Multi-provider LLM support for AI Representation Optimizer.
Supports: Gemini (default), OpenAI, Groq, Ollama.
"""

import os
import json
import re
import time
import requests
from dotenv import load_dotenv

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY   = os.getenv("GROQ_API_KEY")
OLLAMA_URL     = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate")
LLM_PROVIDER   = os.getenv("LLM_PROVIDER", "gemini").split('#')[0].strip()

GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

# ── Prompts ───────────────────────────────────────────────────────────────────

def build_prompt(product: dict, issues: list) -> str:
    issues_str = "\n".join([f"- {i['code']}: {i['message']}" for i in issues])
    
    return f"""
You are an expert e-commerce catalog optimizer for AI Shopping Agents.
Your goal is to rewrite the product data to maximize discoverability and trust for LLMs.

PRODUCT DATA:
Title: {product['title']}
Current Description: {product.get('descriptionPlain', 'Missing')}
Category: {product.get('category', 'General')}
Tags: {', '.join(product.get('tags', []))}

IDENTIFIED ISSUES:
{issues_str}

TASK:
1. Rewrite the Title to be descriptive (50-70 chars), including category and key attribute.
2. Expand the Description to 100-150 words. Include technical specs, materials, and use-cases.
3. Suggest 8-10 high-intent Tags.
4. Provide an SEO Title and Meta Description.
5. Provide a 1-sentence summary of what you improved.

OUTPUT FORMAT:
Return ONLY a valid JSON object with these keys: 
"title", "description", "tags" (array), "seo_title", "seo_description", "changes_summary".
Do NOT include markdown formatting or extra text.
"""

# ── Gemini API caller ─────────────────────────────────────────────────────────

def call_gemini(prompt: str, max_retries: int = 3) -> dict:
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY not set in .env")

    payload = {
        "contents": [{
            "parts": [{"text": prompt}]
        }],
        "generationConfig": {
            "temperature": 0.4,
            "topK": 40,
            "topP": 0.95,
            "maxOutputTokens": 1024,
        }
    }

    for attempt in range(max_retries):
        response = requests.post(
            f"{GEMINI_ENDPOINT}?key={GEMINI_API_KEY}",
            headers={"Content-Type": "application/json"},
            json=payload,
            timeout=30
        )
        
        if response.status_code == 429:
            if attempt < max_retries - 1:
                time.sleep(2 ** attempt)
                continue
            return {"error": "RATE_LIMIT_HIT"}

        if response.status_code != 200:
            raise RuntimeError(f"Gemini API error {response.status_code}: {response.text}")

        data = response.json()
        try:
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Clean JSON if model wrapped it in ```json
            clean_text = re.sub(r"```json|```", "", raw_text).strip()
            return json.loads(clean_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            if attempt < max_retries - 1:
                continue
            raise RuntimeError(f"Failed to parse Gemini response: {e}\nRaw: {data}")

    return {}

# ── OpenAI API caller ─────────────────────────────────────────────────────────

def call_openai(prompt: str, max_retries: int = 3) -> dict:
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY not set in .env")

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }
    payload = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}],
        "response_format": {"type": "json_object"}
    }

    for attempt in range(max_retries):
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        if response.status_code == 200:
            break
        if response.status_code == 429:
            time.sleep(2 ** attempt)
            continue

        raise RuntimeError(f"OpenAI API error {response.status_code}: {response.text}")

    data = response.json()
    raw_text = data["choices"][0]["message"]["content"]
    return json.loads(raw_text)

# ── Groq API caller ───────────────────────────────────────────────────────────

def call_groq(prompt: str) -> dict:
    if not GROQ_API_KEY:
        raise ValueError("GROQ_API_KEY not set in .env")
    
    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            response_format={"type": "json_object"},
        )
        return json.loads(completion.choices[0].message.content)
    except Exception as e:
        raise RuntimeError(f"Groq error: {e}")

# ── Ollama API caller ─────────────────────────────────────────────────────────

def call_ollama(prompt: str) -> dict:
    payload = {
        "model": "llama3",
        "prompt": prompt,
        "stream": False,
        "format": "json"
    }
    try:
        response = requests.post(OLLAMA_URL, json=payload, timeout=60)
        if response.status_code != 200:
            raise RuntimeError(f"Ollama error {response.status_code}: {response.text}")
        return json.loads(response.json()["response"])
    except Exception as e:
        raise RuntimeError(f"Ollama connection failed: {e}")

# ── Selector ──────────────────────────────────────────────────────────────────

def call_llm(prompt: str) -> dict:
    provider = LLM_PROVIDER.lower()
    if provider == "openai": return call_openai(prompt)
    if provider == "groq":   return call_groq(prompt)
    if provider == "ollama": return call_ollama(prompt)
    return call_gemini(prompt)

# ── Main ──────────────────────────────────────────────────────────────────────

def enhance_product(product: dict, issues: list) -> dict:
    prompt = build_prompt(product, issues)
    try:
        improved = call_llm(prompt)
        
        if "error" in improved and improved["error"] == "RATE_LIMIT_HIT":
            return {
                "handle": product["handle"], "title": product["title"], 
                "descriptionHtml": product.get("descriptionHtml"),
                "tags": product.get("tags"), "seo": product.get("seo"),
                "warning": "Rate Limit Hit - No changes applied."
            }

        desc_html = "<p>" + improved.get("description", "").replace("\n\n", "</p><p>") + "</p>"
        
        return {
            "handle":          product["handle"],
            "title":           improved.get("title", product["title"]),
            "descriptionHtml": desc_html,
            "tags":            improved.get("tags", product.get("tags", [])),
            "seo": {
                "title":       improved.get("seo_title", ""),
                "description": improved.get("seo_description", ""),
            },
            "changesSummary":  improved.get("changes_summary", ""),
            "original": {
                "title":       product["title"],
                "description": product.get("descriptionPlain", ""),
                "tags":        product.get("tags", []),
            },
        }
    except Exception as e:
        return {"handle": product["handle"], "error": str(e)}

def enhance_all_products():
    from pathlib import Path
    data_path = Path("data/products.json")
    if not data_path.exists(): return {"stats": {"enhanced": 0, "failed": 0}}
    
    with open(data_path, encoding="utf-8") as f:
        products = json.load(f)["products"]
        
    with open("data/report.json", encoding="utf-8") as f:
        report = json.load(f)
        issues_map = {p["handle"]: p["issues"] for p in report["products"]}
        
    results = []
    stats = {"enhanced": 0, "skipped": 0, "failed": 0}
    
    # Process only first 5 to avoid long wait
    for p in products[:5]:
        print(f"  → Enhancing: {p['title']}...")
        res = enhance_product(p, issues_map.get(p["handle"], []))
        if "error" in res:
            stats["failed"] += 1
        else:
            stats["enhanced"] += 1
        results.append(res)
        
    with open("data/enhanced.json", "w", encoding="utf-8") as f:
        json.dump({"enhancedProducts": results}, f, indent=2, ensure_ascii=False)
        
    return {"stats": stats}