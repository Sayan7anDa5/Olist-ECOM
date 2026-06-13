-- =============================================================================
-- Layer 4: Revenue-at-Risk & Delivery Experience Impact
-- Business questions:
--   1. What share of total revenue sits in At-Risk and Lost RFM segments?
--   2. Does delivery delay correlate with lower review scores (the operational driver)?
--   3. Which product categories or states have the worst delivery performance?
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Revenue concentration by RFM segment
-- Shows how much revenue is held by each customer segment and what fraction
-- is "at risk" (customers who may not return).
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW revenue_by_segment AS
SELECT
    rs.rfm_segment,
    COUNT(DISTINCT rs.customer_unique_id)                       AS customer_count,
    ROUND(SUM(rs.monetary), 2)                                  AS segment_revenue,
    ROUND(
        100.0 * SUM(rs.monetary) / SUM(SUM(rs.monetary)) OVER (),
        2
    )                                                           AS revenue_share_pct,

    -- Flag segments whose revenue is "at risk"
    CASE
        WHEN rs.rfm_segment IN ('At-Risk', 'Lost', 'About to Sleep') THEN 1
        ELSE 0
    END                                                         AS is_at_risk

FROM rfm_segments rs
GROUP BY rs.rfm_segment
ORDER BY segment_revenue DESC;

-- -----------------------------------------------------------------------------
-- Total revenue at risk (single KPI card for the dashboard)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW kpi_revenue_at_risk AS
SELECT
    ROUND(SUM(segment_revenue), 2)                              AS revenue_at_risk,
    ROUND(SUM(revenue_share_pct), 2)                            AS revenue_at_risk_pct
FROM revenue_by_segment
WHERE is_at_risk = 1;

-- -----------------------------------------------------------------------------
-- Delivery delay vs review score
-- Shows the average delivery delay (actual - estimated, in days) bucketed by
-- review score. Positive delay = arrived late.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW delivery_vs_review AS
SELECT
    fr.review_score,
    COUNT(*)                                    AS order_count,
    ROUND(AVG(fr.delivery_delay_days), 2)       AS avg_delivery_delay_days,
    ROUND(MIN(fr.delivery_delay_days), 0)       AS min_delay_days,
    ROUND(MAX(fr.delivery_delay_days), 0)       AS max_delay_days,

    -- Share of orders that arrived late (delay > 0)
    ROUND(
        100.0 * SUM(CASE WHEN fr.delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*),
        2
    )                                           AS late_delivery_pct

FROM fact_reviews fr
WHERE fr.delivery_delay_days IS NOT NULL
GROUP BY fr.review_score
ORDER BY fr.review_score;

-- -----------------------------------------------------------------------------
-- Delivery delay by seller state (geographic view)
-- Helps identify regions driving poor delivery experience.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW delivery_delay_by_seller_state AS
SELECT
    s.seller_state,
    COUNT(DISTINCT fo.order_id)                 AS delivered_order_count,
    ROUND(AVG(fo.delivery_delay_days), 2)       AS avg_delay_days,
    ROUND(
        100.0 * SUM(CASE WHEN fo.delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*),
        2
    )                                           AS late_pct,
    ROUND(AVG(r.review_score), 2)               AS avg_review_score
FROM fact_orders fo
JOIN stg_order_items oi  ON fo.order_id  = oi.order_id
JOIN stg_sellers s       ON oi.seller_id = s.seller_id
LEFT JOIN stg_order_reviews r ON fo.order_id = r.order_id
WHERE fo.order_status = 'delivered'
  AND fo.delivery_delay_days IS NOT NULL
GROUP BY s.seller_state
ORDER BY avg_delay_days DESC;

-- -----------------------------------------------------------------------------
-- Revenue at risk enriched with delivery context
-- Joins RFM segments to average delivery delay experienced by each segment.
-- Hypothesis: At-Risk / Lost customers experienced worse delivery performance.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW segment_delivery_experience AS
SELECT
    rs.rfm_segment,
    COUNT(DISTINCT rs.customer_unique_id)       AS customer_count,
    ROUND(SUM(rs.monetary), 2)                  AS segment_revenue,
    ROUND(AVG(fo.delivery_delay_days), 2)       AS avg_delivery_delay_days,
    ROUND(AVG(r.review_score), 2)               AS avg_review_score,
    ROUND(
        100.0 * SUM(CASE WHEN fo.delivery_delay_days > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(fo.order_id), 0),
        2
    )                                           AS late_delivery_pct
FROM rfm_segments rs
JOIN fact_orders fo
    ON rs.customer_unique_id = fo.customer_unique_id
    AND fo.order_status = 'delivered'
LEFT JOIN stg_order_reviews r ON fo.order_id = r.order_id
GROUP BY rs.rfm_segment
ORDER BY segment_revenue DESC;

-- -----------------------------------------------------------------------------
-- Category-level revenue and delivery performance
-- Answers: which product categories drive the most revenue, and do they have
-- worse-than-average delivery delays?
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW category_revenue_delivery AS
SELECT
    foi.category_en,
    COUNT(DISTINCT fo.order_id)                 AS order_count,
    ROUND(SUM(fo.revenue), 2)                   AS total_revenue,
    ROUND(AVG(fo.delivery_delay_days), 2)       AS avg_delay_days,
    ROUND(AVG(r.review_score), 2)               AS avg_review_score
FROM fact_order_items foi
JOIN fact_orders fo ON foi.order_id = fo.order_id
LEFT JOIN stg_order_reviews r ON fo.order_id = r.order_id
WHERE fo.order_status = 'delivered'
GROUP BY foi.category_en
ORDER BY total_revenue DESC;
