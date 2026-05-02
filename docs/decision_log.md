# Kasparro Hackathon — Decision Log

This log documents the critical "Why" behind our engineering and product choices.

## 1. Product Strategy: One-Click Atomic Fixes vs. Manual Editing
*   **Considered**: A standard dashboard where users can edit fields one by one (Title, Desc, Tags).
*   **Chose**: **Atomic One-Click Full AI Repair**.
*   **Because**: Merchants are overwhelmed. A tool that highlights problems but makes them do the work is just another chore. By providing a one-click "Master Fix" that updates everything simultaneously via the Shopify API, we move from "Analysis" to "Remediation" instantly.

## 2. Metric Engine: ROI-Driven Priority vs. Volume-Driven
*   **Considered**: Sorting store issues by the number of products affected.
*   **Chose**: **ROI Ranking (Total Score Lift)**.
*   **Because**: Fixing a "Missing SKU" for 100 products might have low ROI compared to fixing "Missing Images" for 10 products. We prioritized fixes that give the highest point lift to the store's composite score, ensuring the merchant works on what actually moves the needle for AI agents.

## 3. Real-Time Feedback: Live Rescore vs. Cached Analysis
*   **Considered**: Running the AI analysis once and showing a static report.
*   **Chose**: **Live Pipeline Re-analysis**.
*   **Because**: In the agentic era, data changes fast. When a user clicks "Apply Fix," they need to see their score jump from 40 to 100 **instantly**. We implemented a cache-busting live simulation that re-runs the analyzer the moment a Shopify sync is confirmed.

## 4. Search Simulation: Category Gatekeeping vs. Raw Keywords
*   **Considered**: A simple keyword search simulator.
*   **Chose**: **Category-Aware Signal Matching**.
*   **Because**: AI search agents (Perplexity/GPT) don't just look for words; they understand intent. We built "Category Gates" (e.g., Hoodie vs. Kurta) to ensure that products only match relevant queries, preventing "fake" visibility scores and ensuring high-precision discovery.

## 5. UI Design: Glassmorphism & High-Density Insights
*   **Considered**: A standard Bootstrap/Tailwind admin template.
*   **Chose**: **Premium Dark Mode + Glassmorphism**.
*   **Because**: Trust is everything in AI. A premium, high-tech aesthetic communicates that the tool is sophisticated and "agent-ready." We used vibrant signal strengths (Strong/Weak) and score pills to make the data feel alive.
