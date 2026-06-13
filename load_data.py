"""
Ingest Olist Brazilian E-Commerce CSVs into MySQL (or PostgreSQL).

Usage:
    python load_data.py --host localhost --db olist --user root --password secret
    python load_data.py --host localhost --db olist --user root --password secret --dialect postgresql

The script truncates and reloads each table on every run (idempotent).
Place all 9 Olist CSVs in the data/ directory before running.
"""

import argparse
import os
import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text
from tqdm import tqdm

DATA_DIR = Path(__file__).parent / "data"

# Map CSV filename stem → staging table name
CSV_TABLE_MAP = {
    "olist_customers_dataset":                  "stg_customers",
    "olist_orders_dataset":                     "stg_orders",
    "olist_order_items_dataset":                "stg_order_items",
    "olist_order_payments_dataset":             "stg_order_payments",
    "olist_order_reviews_dataset":              "stg_order_reviews",
    "olist_products_dataset":                   "stg_products",
    "olist_sellers_dataset":                    "stg_sellers",
    "olist_geolocation_dataset":                "stg_geolocation",
    "product_category_name_translation":        "stg_product_category_translation",
}

TIMESTAMP_COLUMNS = {
    "stg_orders": [
        "order_purchase_timestamp",
        "order_approved_at",
        "order_delivered_carrier_date",
        "order_delivered_customer_date",
        "order_estimated_delivery_date",
    ],
    "stg_order_reviews": ["review_creation_date", "review_answer_timestamp"],
    "stg_order_items":   ["shipping_limit_date"],
}


def build_engine(dialect: str, host: str, port: int, db: str, user: str, password: str):
    if dialect == "mysql":
        url = f"mysql+pymysql://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"
    elif dialect == "postgresql":
        url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    else:
        sys.exit(f"Unsupported dialect: {dialect}")
    return create_engine(url, echo=False)


def find_csv(stem: str) -> Path | None:
    for path in DATA_DIR.glob("*.csv"):
        if path.stem == stem:
            return path
    return None


def load_table(engine, stem: str, table: str, chunksize: int = 50_000):
    csv_path = find_csv(stem)
    if csv_path is None:
        print(f"  [SKIP] {stem}.csv not found in data/")
        return

    df = pd.read_csv(csv_path, low_memory=False)

    for col in TIMESTAMP_COLUMNS.get(table, []):
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")

    with engine.begin() as conn:
        conn.execute(text(f"DELETE FROM {table}"))

    df.to_sql(table, engine, if_exists="append", index=False, chunksize=chunksize, method="multi")
    print(f"  [OK]   {table:40s} {len(df):>8,} rows")


def main():
    parser = argparse.ArgumentParser(description="Load Olist CSVs into the database.")
    parser.add_argument("--host",     default="localhost")
    parser.add_argument("--port",     type=int, default=None)
    parser.add_argument("--db",       default="olist")
    parser.add_argument("--user",     required=True)
    parser.add_argument("--password", required=True)
    parser.add_argument("--dialect",  default="mysql", choices=["mysql", "postgresql"])
    args = parser.parse_args()

    port = args.port or (5432 if args.dialect == "postgresql" else 3306)
    engine = build_engine(args.dialect, args.host, port, args.db, args.user, args.password)

    print(f"\nConnected to {args.dialect}://{args.host}:{port}/{args.db}")
    print("Loading tables...\n")

    for stem, table in tqdm(CSV_TABLE_MAP.items(), desc="Tables", unit="table"):
        load_table(engine, stem, table)

    print("\nDone. Run the SQL pipeline next:\n")
    print("  01_schema_staging.sql  →  02_clean_conform.sql  →  03_rfm_segmentation.sql")
    print("  →  04_cohort_retention.sql  →  05_revenue_at_risk.sql")


if __name__ == "__main__":
    main()
