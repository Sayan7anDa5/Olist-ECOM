-- =============================================================================
-- Layer 2: Raw / Staging Tables  (PostgreSQL)
-- Declares types, primary keys, foreign keys, and indexes on join columns.
-- Run once on a fresh database after load_data.py has loaded the CSVs.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Customers
-- customer_unique_id is the stable identity; customer_id is per-order.
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id              VARCHAR(50)  NOT NULL,
    customer_unique_id       VARCHAR(50)  NOT NULL,
    customer_zip_code_prefix VARCHAR(10)  NOT NULL,
    customer_city            VARCHAR(100) NOT NULL,
    customer_state           CHAR(2)      NOT NULL,
    PRIMARY KEY (customer_id)
);
CREATE INDEX IF NOT EXISTS idx_customer_unique_id ON stg_customers (customer_unique_id);

-- -----------------------------------------------------------------------------
-- Orders
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_orders (
    order_id                        VARCHAR(50) NOT NULL,
    customer_id                     VARCHAR(50) NOT NULL,
    order_status                    VARCHAR(20) NOT NULL,
    order_purchase_timestamp        TIMESTAMP,
    order_approved_at               TIMESTAMP,
    order_delivered_carrier_date    TIMESTAMP,
    order_delivered_customer_date   TIMESTAMP,
    order_estimated_delivery_date   TIMESTAMP,
    PRIMARY KEY (order_id)
);
CREATE INDEX IF NOT EXISTS idx_orders_customer_id  ON stg_orders (customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status       ON stg_orders (order_status);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts  ON stg_orders (order_purchase_timestamp);

-- -----------------------------------------------------------------------------
-- Order Items
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_order_items (
    order_id            VARCHAR(50)   NOT NULL,
    order_item_id       INT           NOT NULL,
    product_id          VARCHAR(50)   NOT NULL,
    seller_id           VARCHAR(50)   NOT NULL,
    shipping_limit_date TIMESTAMP,
    price               NUMERIC(10,2) NOT NULL,
    freight_value       NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (order_id, order_item_id)
);
CREATE INDEX IF NOT EXISTS idx_items_product_id ON stg_order_items (product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller_id  ON stg_order_items (seller_id);

-- -----------------------------------------------------------------------------
-- Order Payments
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_order_payments (
    order_id             VARCHAR(50)   NOT NULL,
    payment_sequential   INT           NOT NULL,
    payment_type         VARCHAR(30)   NOT NULL,
    payment_installments INT           NOT NULL,
    payment_value        NUMERIC(10,2) NOT NULL,
    PRIMARY KEY (order_id, payment_sequential)
);
CREATE INDEX IF NOT EXISTS idx_payments_order_id ON stg_order_payments (order_id);

-- -----------------------------------------------------------------------------
-- Order Reviews
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_order_reviews (
    review_id               VARCHAR(50) NOT NULL,
    order_id                VARCHAR(50) NOT NULL,
    review_score            SMALLINT    NOT NULL,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TIMESTAMP,
    review_answer_timestamp TIMESTAMP,
    PRIMARY KEY (review_id)
);
CREATE INDEX IF NOT EXISTS idx_reviews_order_id ON stg_order_reviews (order_id);

-- -----------------------------------------------------------------------------
-- Products
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_products (
    product_id                 VARCHAR(50)  NOT NULL,
    product_category_name      VARCHAR(100),
    product_name_lenght        INT,
    product_description_lenght INT,
    product_photos_qty         INT,
    product_weight_g           INT,
    product_length_cm          INT,
    product_height_cm          INT,
    product_width_cm           INT,
    PRIMARY KEY (product_id)
);

-- -----------------------------------------------------------------------------
-- Sellers
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_sellers (
    seller_id              VARCHAR(50)  NOT NULL,
    seller_zip_code_prefix VARCHAR(10)  NOT NULL,
    seller_city            VARCHAR(100) NOT NULL,
    seller_state           CHAR(2)      NOT NULL,
    PRIMARY KEY (seller_id)
);

-- -----------------------------------------------------------------------------
-- Geolocation
-- No PK — zip codes repeat (multiple lat/lng points per zip).
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_geolocation (
    geolocation_zip_code_prefix VARCHAR(10)   NOT NULL,
    geolocation_lat             NUMERIC(10,6) NOT NULL,
    geolocation_lng             NUMERIC(10,6) NOT NULL,
    geolocation_city            VARCHAR(100)  NOT NULL,
    geolocation_state           CHAR(2)       NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_geo_zip ON stg_geolocation (geolocation_zip_code_prefix);

-- -----------------------------------------------------------------------------
-- Product Category Name Translation (PT → EN)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS stg_product_category_translation (
    product_category_name         VARCHAR(100) NOT NULL,
    product_category_name_english VARCHAR(100) NOT NULL,
    PRIMARY KEY (product_category_name)
);
