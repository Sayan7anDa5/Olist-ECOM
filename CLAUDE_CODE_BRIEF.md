# Build Brief: Customer Value Segmentation & Revenue-at-Risk Analysis

## Goal
A SQL-driven analytics project on the Olist Brazilian E-Commerce dataset, demonstrating
window functions, CTEs, RFM segmentation, cohort retention, and revenue concentration.
Output feeds a Power BI dashboard. Build it as a layered (medallion) pipeline.

## Stack
- Database: MySQL 8+ (window functions required). PostgreSQL also fine — keep SQL portable.
- Language for data load: Python (pandas) to ingest CSVs into the DB.
- Dashboard: Power BI (.pbix) connecting to the analytical views only.

## Dataset
Olist Brazilian E-Commerce (Kaggle: "olister/brazilian-ecommerce"). 9 CSVs:
customers, orders, order_items, order_payments, order_reviews, products, sellers,
geolocation, product_category_name_translation. ~100K orders, 2016–2018.

## CRITICAL DECISIONS — do not deviate
1. **Identity:** Olist assigns a NEW `customer_id` per order. `customer_unique_id` is the
   stable customer identity. ALL customer-level aggregation (RFM, frequency, cohorts) MUST
   group by `customer_unique_id`, never `customer_id`. Getting this wrong makes every
   customer look like a one-time buyer.
2. **Revenue scope:** Only `order_status = 'delivered'` orders count toward revenue/monetary
   metrics. Exclude cancelled/unavailable.
3. **Framing:** This is NOT a pure churn project — Olist is single-purchase-dominant (~3%
   repeat rate). Treat low retention as a FINDING, not a bug. Lead with RFM value
   segmentation + delivery-experience impact + revenue concentration.
4. **Layer separation:** Raw staging tables → cleaned views → analytical views. The
   dashboard connects ONLY to analytical views, never raw tables.

## Architecture (5 layers)
1. Source — the 9 raw CSVs.
2. Raw/staging — one table per CSV, declared types, PKs/FKs, indexes on join columns
   (order_id, customer_id, product_id, seller_id).
3. Cleaned/conformed — collapse to customer_unique_id, cast timestamps to datetime,
   translate category names PT→EN, filter delivered orders. Produce a clean `fact_orders` view.
4. Analytical marts — RFM, cohort retention, delivery-vs-review, revenue-at-risk.
5. Presentation — Power BI on the mart views.

## File structure
```
customer-value-analysis/
├── README.md
├── load_data.py                  # ingest CSVs → DB
├── requirements.txt
├── sql/
│   ├── 01_schema_staging.sql     # Layer 2: tables, types, keys, indexes
│   ├── 02_clean_conform.sql      # Layer 3: cleaned views incl. fact_orders
│   ├── 03_rfm_segmentation.sql   # Layer 4
│   ├── 04_cohort_retention.sql   # Layer 4
│   └── 05_revenue_at_risk.sql    # Layer 4
├── data/                         # gitignored; CSVs or a download note
├── dashboard/                    # customer_value.pbix
└── images/                       # dashboard screenshots for README
```

## What each analytical file must produce
- **03_rfm_segmentation.sql** — per customer_unique_id: Recency (days since last delivered
  order, via window function over order dates), Frequency (delivered order count), Monetary
  (sum of payment_value). Then CASE-based segments: Champions, Loyal, At-Risk, Lost.
- **04_cohort_retention.sql** — assign each customer to their first-purchase month (CTE),
  compute month-over-month repeat-purchase rate. Expose the cohort grid as a view.
- **05_revenue_at_risk.sql** — % of total revenue concentrated in each RFM segment;
  highlight revenue sitting in At-Risk + Lost. Join delivery delay (actual vs estimated
  delivery date) to average review_score to show the driver.

## Deliverable expectations
- Every SQL file runnable top-to-bottom on a fresh DB after load_data.py.
- Comment each query block with the business question it answers.
- README: problem statement, architecture summary, key findings (with real numbers from
  the data), tech stack, how-to-run. No placeholder text — fill real values.
