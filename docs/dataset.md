# Dataset Design

## Overview

We created a synthetic Shopify dataset to simulate a real-world "Everyday Essentials" store with realistic data quality issues.

The goal is to test how AI systems interpret imperfect product data.

---

## Dataset Composition

* Total Products: 30
* Clean Products: 8 (~25%)
* Flawed Products: 22 (~75%)

---

## Categories Covered

* Clothing
* Shoes
* Skincare
* Electronics
* Accessories

---

## Data Quality Strategy

The dataset intentionally includes realistic issues commonly found in Shopify stores.

### Types of Issues Introduced

1. Missing attributes

   A significant portion of the dataset includes products that lack essential attributes required for proper understanding and comparison. For example, clothing items such as shirts and kurtas are listed without specifying size ranges, fabric type (cotton, polyester, etc.), or fit (regular, slim, oversized). Similarly, electronics like laptops and speakers are missing key specifications such as RAM, storage, battery life, or connectivity features. This simulates real-world seller behavior where listings are incomplete due to time constraints or lack of expertise.

2. Vague descriptions

   Many products contain descriptions that are overly generic and fail to communicate meaningful information. Examples include phrases like "good product", "best quality", or "very useful item" without any supporting details. These descriptions do not explain the product’s use-case, benefits, or differentiators, making it difficult for both users and AI systems to understand the product’s value. This reflects common low-effort listings found in real Shopify stores.

3. Contradictions

   Some products intentionally contain mismatches between the title and the description. For instance, a product titled "Winter Jacket" may have a description suggesting it is suitable for summer wear, or a "Bluetooth Speaker" may be described as a wired device. These contradictions simulate real-world data inconsistencies caused by copy-paste errors or incorrect product updates, which can confuse AI interpretation systems.

4. Formatting issues

   The dataset includes multiple formatting inconsistencies such as missing spaces (e.g., "Bestsoundquality"), inconsistent capitalization (e.g., "PREMIUM quality product"), and poorly structured sentences. These issues are subtle but impactful, as they degrade readability and can affect how AI models tokenize and interpret the text. This mirrors real-world listings where sellers do not follow consistent formatting standards.

5. Overloaded descriptions

   Some products contain excessively long and unstructured descriptions that combine multiple ideas into a single paragraph without clear separation. These descriptions often include redundant phrases, repeated keywords, and lack logical flow. For example, a single sentence may attempt to describe features, benefits, and usage scenarios all at once. This simulates listings where sellers try to maximize keyword usage without focusing on clarity.

6. Missing trust signals

   Certain product categories, especially skincare and personal care, are intentionally missing critical trust-building information. For example, a face cream may not list its ingredients, skin type suitability, or safety certifications. This reflects real-world scenarios where incomplete information reduces buyer confidence and makes it harder for AI systems to assess product reliability.

7. Duplicate-like products

   The dataset includes multiple products that are nearly identical but have slight variations in naming or description. For example, "Cotton Casual Shirt" and "Casual Cotton Shirt" may refer to similar items with minimal differentiation. These duplicates simulate real catalog redundancy, where sellers upload similar products multiple times with minor changes, leading to confusion in product grouping and recommendation systems.

---

## Shopify Setup

The Shopify store was created using a Shopify Partner account to allow full development access  .A development store  was initialized to simulate a real merchant environment.

### Product Import Process

* Products were generated externally using a structured CSV file.
* The CSV followed Shopify’s official import format with strict adherence to column names and ordering.
* The file was uploaded via the Shopify Admin panel under Products → Import.
* After import, products were verified manually to ensure:

  * No column misalignment
  * Correct mapping of fields (Title, Description, Price, etc.)
  * Proper handling of empty fields (especially Image Src)

### Taxonomy and Categorization

* All products were assigned categories using Shopify’s standardized product taxonomy.
* Only predefined category paths were used to maintain consistency and avoid ambiguity.
* Categories were selected to reflect realistic e-commerce groupings such as clothing, electronics, and personal care.

### Data Validation

* After import, the dataset was reviewed inside Shopify to confirm:

  * Products appeared correctly in the admin dashboard
  * Pricing values were properly parsed as numeric
  * Descriptions rendered correctly without formatting issues
  * Images loaded correctly where provided
  * Products without images remained intentionally blank

### Purpose of Setup

This setup ensures that the dataset behaves like a real Shopify store, allowing accurate testing of how AI systems interpret product data in a production-like environment.

---

## Purpose

This dataset serves as the foundation for:

* AI interpretation testing
* Gap detection
* Recommendation generation
* Prioritization logic

---

## Key Insight

The dataset is not artificially broken — it reflects realistic human errors, incomplete data, and inconsistent product representation commonly found in e-commerce stores.
