"""
Export all analytical view data from PostgreSQL to parquet files.
Run once locally after the SQL pipeline to generate static data for the web dashboard.

Usage:  python3 export_data.py
Output: dashboard/data/*.parquet
"""

from pathlib import Path
import pandas as pd
from sqlalchemy import create_engine, text

OUT_DIR = Path(__file__).parent / "dashboard" / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    "postgresql+psycopg2://sayantan@/olist?host=/var/run/postgresql"
)

EXPORTS = {
    "rfm_segment_summary":          "SELECT * FROM rfm_segment_summary",
    "kpi_revenue_at_risk":          "SELECT * FROM kpi_revenue_at_risk",
    "delivery_vs_review":           "SELECT * FROM delivery_vs_review ORDER BY review_score",
    "segment_delivery_experience":  "SELECT * FROM segment_delivery_experience ORDER BY segment_revenue DESC",
    "category_revenue_delivery":    "SELECT * FROM category_revenue_delivery ORDER BY total_revenue DESC LIMIT 15",
    "delivery_delay_by_seller_state": "SELECT * FROM delivery_delay_by_seller_state ORDER BY avg_delay_days DESC LIMIT 20",
    "cohort_retention_rates":       "SELECT * FROM cohort_retention_rates WHERE period_number <= 6",
    "cohort_avg_retention":         "SELECT * FROM cohort_avg_retention WHERE period_number <= 6",
    "totals": """
        SELECT
            COUNT(*)                           AS total_orders,
            ROUND(SUM(revenue)::numeric, 0)    AS total_revenue,
            COUNT(DISTINCT customer_unique_id) AS total_customers
        FROM fact_orders WHERE order_status = 'delivered'
    """,
    "repeat_rate": """
        SELECT ROUND(
            100.0 * SUM(CASE WHEN frequency > 1 THEN 1 ELSE 0 END) / COUNT(*)::numeric, 1
        ) AS repeat_pct
        FROM rfm_raw
    """,
}

with engine.connect() as conn:
    for name, sql in EXPORTS.items():
        df = pd.read_sql(text(sql), conn)
        path = OUT_DIR / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"  {name:40s} {len(df):>6} rows → {path.name}")

print(f"\nExported {len(EXPORTS)} files to {OUT_DIR}/")
