-- =============================================================================
-- Layer 3: Cleaned / Conformed Views  (PostgreSQL)
-- - Collapses customer_id → customer_unique_id
-- - Translates product category names PT → EN
-- - Computes delivery delay with date subtraction (PostgreSQL returns integer days)
-- - Filters to delivered orders only for revenue-bearing columns
-- - Produces fact_orders as the single source of truth for Layer 4
-- =============================================================================

-- -----------------------------------------------------------------------------
-- dim_customers: one row per customer_unique_id with latest known city/state
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_customers AS
SELECT
    customer_unique_id,
    MAX(customer_city)  AS customer_city,
    MAX(customer_state) AS customer_state
FROM stg_customers
GROUP BY customer_unique_id;

-- -----------------------------------------------------------------------------
-- dim_products: with English category names
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW dim_products AS
SELECT
    p.product_id,
    COALESCE(t.product_category_name_english, p.product_category_name, 'unknown') AS category_en,
    p.product_weight_g,
    p.product_photos_qty
FROM stg_products p
LEFT JOIN stg_product_category_translation t
    ON p.product_category_name = t.product_category_name;

-- -----------------------------------------------------------------------------
-- fact_orders: one row per order joined to customer_unique_id and payments.
-- SCOPE: all statuses — filtering to 'delivered' happens in the marts.
-- Revenue is NULL for non-delivered orders.
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_orders AS
SELECT
    o.order_id,
    c.customer_unique_id,
    o.order_status,
    o.order_purchase_timestamp,
    o.order_approved_at,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,

    -- PostgreSQL date subtraction returns integer days directly
    (o.order_delivered_customer_date::date - o.order_estimated_delivery_date::date)
        AS delivery_delay_days,

    pay.total_payment_value,

    CASE
        WHEN o.order_status = 'delivered' THEN pay.total_payment_value
        ELSE NULL
    END AS revenue

FROM stg_orders o
JOIN stg_customers c
    ON o.customer_id = c.customer_id
LEFT JOIN (
    SELECT order_id, SUM(payment_value) AS total_payment_value
    FROM stg_order_payments
    GROUP BY order_id
) pay ON o.order_id = pay.order_id;

-- -----------------------------------------------------------------------------
-- fact_order_items: order items enriched with English product category
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_order_items AS
SELECT
    oi.order_id,
    oi.order_item_id,
    oi.product_id,
    oi.seller_id,
    dp.category_en,
    oi.price,
    oi.freight_value,
    oi.price + oi.freight_value AS item_total
FROM stg_order_items oi
LEFT JOIN dim_products dp ON oi.product_id = dp.product_id;

-- -----------------------------------------------------------------------------
-- fact_reviews: reviews joined to orders to get customer_unique_id
-- -----------------------------------------------------------------------------
CREATE OR REPLACE VIEW fact_reviews AS
SELECT
    r.review_id,
    r.order_id,
    fo.customer_unique_id,
    r.review_score,
    r.review_creation_date,
    fo.order_delivered_customer_date,
    fo.delivery_delay_days
FROM stg_order_reviews r
JOIN fact_orders fo ON r.order_id = fo.order_id;
