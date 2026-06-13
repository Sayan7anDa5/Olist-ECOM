-- =============================================================================
-- Layer 4: Revenue-at-Risk & Delivery Experience Impact  (PostgreSQL)
-- Business questions:
--   1. What share of total revenue sits in At-Risk and Lost RFM segments?
--   2. Does delivery delay correlate with lower review scores?
--   3. Which product categories or states have the worst delivery performance?
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Revenue concentration by RFM segment
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW revenue_by_segment AS
SELECT
    rs.rfm_segment,
    COUNT(DISTINCT rs.customer_unique_id)                           AS customer_count,
    ROUND(SUM(rs.monetary)::numeric, 2)                            AS segment_revenue,
    ROUND(
        (100.0 * SUM(rs.monetary) / SUM(SUM(rs.monetary)) OVER ())::numeric,
        2
    )                                                              AS revenue_share_pct,
    CASE
        WHEN rs.rfm_segment IN ('At-Risk', 'Lost', 'About to Sleep') THEN 1
        ELSE 0
    END                                                            AS is_at_risk
FROM rfm_segments rs
GROUP BY rs.rfm_segment
ORDER BY segment_revenue DESC;

-- -----------------------------------------------------------------------------
-- Total revenue at risk (single KPI card for the dashboard)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW kpi_revenue_at_risk AS
SELECT
    ROUND(SUM(segment_revenue)::numeric, 2)   AS revenue_at_risk,
    ROUND(SUM(revenue_share_pct)::numeric, 2) AS revenue_at_risk_pct
FROM revenue_by_segment
WHERE is_at_risk = 1;

-- -----------------------------------------------------------------------------
-- Delivery delay vs review score
-- Positive delay = arrived late; shows the operational driver of dissatisfaction.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW delivery_vs_review AS
SELECT
    fr.review_score,
    COUNT(*)                                                    AS order_count,
    ROUND(AVG(fr.delivery_delay_days)::numeric, 2)              AS avg_delivery_delay_days,
    ROUND(MIN(fr.delivery_delay_days)::numeric, 0)              AS min_delay_days,
    ROUND(MAX(fr.delivery_delay_days)::numeric, 0)              AS max_delay_days,
    ROUND(
        (100.0 * SUM(CASE WHEN fr.delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*))::numeric,
        2
    )                                                           AS late_delivery_pct
FROM fact_reviews fr
WHERE fr.delivery_delay_days IS NOT NULL
GROUP BY fr.review_score
ORDER BY fr.review_score;

-- -----------------------------------------------------------------------------
-- Delivery delay by seller state (geographic view)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW delivery_delay_by_seller_state AS
SELECT
    s.seller_state,
    COUNT(DISTINCT fo.order_id)                                 AS delivered_order_count,
    ROUND(AVG(fo.delivery_delay_days)::numeric, 2)              AS avg_delay_days,
    ROUND(
        (100.0 * SUM(CASE WHEN fo.delivery_delay_days > 0 THEN 1 ELSE 0 END) / COUNT(*))::numeric,
        2
    )                                                           AS late_pct,
    ROUND(AVG(r.review_score)::numeric, 2)                      AS avg_review_score
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
-- Hypothesis: At-Risk/Lost customers experienced worse delivery performance.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW segment_delivery_experience AS
SELECT
    rs.rfm_segment,
    COUNT(DISTINCT rs.customer_unique_id)                       AS customer_count,
    ROUND(SUM(rs.monetary)::numeric, 2)                         AS segment_revenue,
    ROUND(AVG(fo.delivery_delay_days)::numeric, 2)              AS avg_delivery_delay_days,
    ROUND(AVG(r.review_score)::numeric, 2)                      AS avg_review_score,
    ROUND(
        (100.0 * SUM(CASE WHEN fo.delivery_delay_days > 0 THEN 1 ELSE 0 END)
        / NULLIF(COUNT(fo.order_id), 0))::numeric,
        2
    )                                                           AS late_delivery_pct
FROM rfm_segments rs
JOIN fact_orders fo
    ON rs.customer_unique_id = fo.customer_unique_id
   AND fo.order_status = 'delivered'
LEFT JOIN stg_order_reviews r ON fo.order_id = r.order_id
GROUP BY rs.rfm_segment
ORDER BY segment_revenue DESC;

-- -----------------------------------------------------------------------------
-- Category-level revenue and delivery performance
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW category_revenue_delivery AS
SELECT
    foi.category_en,
    COUNT(DISTINCT fo.order_id)                                 AS order_count,
    ROUND(SUM(fo.revenue)::numeric, 2)                          AS total_revenue,
    ROUND(AVG(fo.delivery_delay_days)::numeric, 2)              AS avg_delay_days,
    ROUND(AVG(r.review_score)::numeric, 2)                      AS avg_review_score
FROM fact_order_items foi
JOIN fact_orders fo ON foi.order_id = fo.order_id
LEFT JOIN stg_order_reviews r ON fo.order_id = r.order_id
WHERE fo.order_status = 'delivered'
GROUP BY foi.category_en
ORDER BY total_revenue DESC;
