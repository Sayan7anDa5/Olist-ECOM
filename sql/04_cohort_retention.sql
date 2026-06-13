-- =============================================================================
-- Layer 4: Cohort Retention  (PostgreSQL)
-- Business question: Of customers who first purchased in month X, what fraction
--                   returned in subsequent months?
--
-- Olist context: ~3% repeat rate is expected — treat it as a finding.
-- Scope: delivered orders only.
-- Identity: customer_unique_id.
-- Months stored as DATE (first day of month) for clean arithmetic.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Step 1: Assign each customer to their first-purchase cohort month
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cohort_base AS
SELECT
    customer_unique_id,
    DATE_TRUNC('month', MIN(order_purchase_timestamp))::date AS cohort_month,
    MIN(order_purchase_timestamp)                             AS first_order_date
FROM fact_orders
WHERE order_status = 'delivered'
GROUP BY customer_unique_id;

-- -----------------------------------------------------------------------------
-- Step 2: All delivered order months per customer
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW customer_order_months AS
SELECT DISTINCT
    customer_unique_id,
    DATE_TRUNC('month', order_purchase_timestamp)::date AS order_month
FROM fact_orders
WHERE order_status = 'delivered';

-- -----------------------------------------------------------------------------
-- Step 3: Cohort grid — months since first purchase (period_number)
-- period_number = 0 → acquisition month (always 100%)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cohort_retention_grid AS
SELECT
    cb.cohort_month,
    -- Month difference: extract years and months from the age interval
    (EXTRACT(YEAR  FROM AGE(com.order_month, cb.cohort_month)) * 12
     + EXTRACT(MONTH FROM AGE(com.order_month, cb.cohort_month)))::int AS period_number,
    COUNT(DISTINCT cb.customer_unique_id)                              AS retained_customers
FROM cohort_base cb
JOIN customer_order_months com
    ON cb.customer_unique_id = com.customer_unique_id
   AND com.order_month >= cb.cohort_month
GROUP BY cb.cohort_month, period_number;

-- -----------------------------------------------------------------------------
-- Step 4: Cohort sizes (denominator for retention rate)
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cohort_sizes AS
SELECT
    cohort_month,
    COUNT(DISTINCT customer_unique_id) AS cohort_size
FROM cohort_base
GROUP BY cohort_month;

-- -----------------------------------------------------------------------------
-- Step 5: Retention rates — the final output for the dashboard cohort matrix
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cohort_retention_rates AS
SELECT
    TO_CHAR(g.cohort_month, 'YYYY-MM')                          AS cohort_month,
    g.period_number,
    g.retained_customers,
    s.cohort_size,
    ROUND(100.0 * g.retained_customers / s.cohort_size, 2)      AS retention_pct
FROM cohort_retention_grid g
JOIN cohort_sizes s ON g.cohort_month = s.cohort_month
ORDER BY g.cohort_month, g.period_number;

-- -----------------------------------------------------------------------------
-- Summary: average retention rate at each period across all cohorts
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW cohort_avg_retention AS
SELECT
    period_number,
    ROUND(AVG(retention_pct)::numeric, 2) AS avg_retention_pct,
    SUM(retained_customers)               AS total_retained,
    SUM(cohort_size)                      AS total_cohort_size
FROM cohort_retention_rates
GROUP BY period_number
ORDER BY period_number;
