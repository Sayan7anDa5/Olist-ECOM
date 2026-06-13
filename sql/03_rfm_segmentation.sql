-- =============================================================================
-- Layer 4: RFM Segmentation  (PostgreSQL)
-- Business question: Which customers are Champions, Loyal, At-Risk, or Lost
--                   based on their purchase recency, frequency, and spend?
--
-- Scope: delivered orders only.
-- Identity: customer_unique_id (stable across multiple orders).
-- Reference date: latest order_purchase_timestamp in the dataset.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Step 1: Raw RFM metrics per customer
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW rfm_raw AS
WITH reference_date AS (
    SELECT MAX(order_purchase_timestamp) AS ref_date
    FROM fact_orders
    WHERE order_status = 'delivered'
),
delivered_orders AS (
    SELECT customer_unique_id, order_purchase_timestamp, revenue
    FROM fact_orders
    WHERE order_status = 'delivered'
)
SELECT
    d.customer_unique_id,
    -- PostgreSQL date subtraction returns integer days
    (r.ref_date::date - MAX(d.order_purchase_timestamp)::date) AS recency_days,
    COUNT(*)                                                    AS frequency,
    SUM(d.revenue)                                              AS monetary
FROM delivered_orders d
CROSS JOIN reference_date r
GROUP BY d.customer_unique_id, r.ref_date;

-- -----------------------------------------------------------------------------
-- Step 2: RFM quintile scores (1–5) using NTILE window functions
-- Higher score = better for all three dimensions.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW rfm_scores AS
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    ROUND(monetary::numeric, 2)                               AS monetary,
    -- R score: invert so smaller recency_days = higher score
    6 - NTILE(5) OVER (ORDER BY recency_days ASC)             AS r_score,
    NTILE(5) OVER (ORDER BY frequency        ASC)             AS f_score,
    NTILE(5) OVER (ORDER BY monetary         ASC)             AS m_score
FROM rfm_raw;

-- -----------------------------------------------------------------------------
-- Step 3: RFM segments
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW rfm_segments AS
SELECT
    customer_unique_id,
    recency_days,
    frequency,
    monetary,
    r_score,
    f_score,
    m_score,
    r_score + f_score + m_score AS rfm_total,

    CASE
        WHEN r_score >= 4 AND f_score >= 4  THEN 'Champions'
        WHEN r_score >= 3 AND f_score >= 3  THEN 'Loyal'
        WHEN r_score >= 4 AND f_score <= 2  THEN 'Promising'
        WHEN r_score =  3 AND f_score >= 2  THEN 'Needs Attention'
        WHEN r_score <= 2 AND f_score >= 3  THEN 'At-Risk'
        WHEN r_score =  2 AND f_score <= 2  THEN 'About to Sleep'
        WHEN r_score =  1                   THEN 'Lost'
        ELSE 'Others'
    END AS rfm_segment

FROM rfm_scores;

-- -----------------------------------------------------------------------------
-- Segment summary: customer count and total revenue per segment
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW rfm_segment_summary AS
SELECT
    rfm_segment,
    COUNT(*)                                         AS customer_count,
    ROUND(SUM(monetary)::numeric, 2)                 AS total_revenue,
    ROUND(AVG(monetary)::numeric, 2)                 AS avg_revenue_per_customer,
    ROUND(AVG(recency_days)::numeric, 1)             AS avg_recency_days,
    ROUND(AVG(frequency::numeric), 2)                AS avg_frequency
FROM rfm_segments
GROUP BY rfm_segment
ORDER BY total_revenue DESC;
