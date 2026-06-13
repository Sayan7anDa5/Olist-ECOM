"""
Olist Customer Value Segmentation Dashboard
Loads pre-exported parquet files from dashboard/data/ — no database required.
Run with:  streamlit run dashboard/app.py
"""

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Olist Customer Value Analysis",
    page_icon="📦",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Data loading (cached) ─────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data
def load(name: str) -> pd.DataFrame:
    return pd.read_parquet(DATA_DIR / f"{name}.parquet")

rfm        = load("rfm_segment_summary")
kpi_risk   = load("kpi_revenue_at_risk")
dlv_rev    = load("delivery_vs_review")
seg_dlv    = load("segment_delivery_experience")
cat_rev    = load("category_revenue_delivery")
state_dlv  = load("delivery_delay_by_seller_state")
cohort     = load("cohort_retention_rates")
cohort_avg = load("cohort_avg_retention")
totals     = load("totals")
repeat     = load("repeat_rate")

# ── Colour palette ────────────────────────────────────────────────────────────
SEGMENT_COLORS = {
    "Champions":      "#2ecc71",
    "Loyal":          "#27ae60",
    "Promising":      "#3498db",
    "Needs Attention":"#f39c12",
    "About to Sleep": "#e67e22",
    "At-Risk":        "#e74c3c",
    "Lost":           "#c0392b",
    "Others":         "#95a5a6",
}

# ── Title ─────────────────────────────────────────────────────────────────────
st.title("📦 Olist Customer Value Segmentation")
st.caption("Olist Brazilian E-Commerce · 2016–2018 · delivered orders only")
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Delivered Orders",     f"{int(totals['total_orders'][0]):,}")
c2.metric("Total Revenue",        f"R$ {int(totals['total_revenue'][0]):,}")
c3.metric("Unique Customers",     f"{int(totals['total_customers'][0]):,}")
c4.metric("Revenue at Risk",      f"{float(kpi_risk['revenue_at_risk_pct'][0]):.1f}%",
          delta=f"R$ {float(kpi_risk['revenue_at_risk'][0]):,.0f}",
          delta_color="inverse")
c5.metric("Repeat Purchase Rate", f"{float(repeat['repeat_pct'][0]):.1f}%")

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# Section 1 — RFM Segmentation
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("RFM Customer Segmentation")
col_left, col_right = st.columns([3, 2])

with col_left:
    colors = [SEGMENT_COLORS.get(s, "#95a5a6") for s in rfm["rfm_segment"]]
    fig = go.Figure(go.Bar(
        x=rfm["rfm_segment"],
        y=rfm["total_revenue"],
        marker_color=colors,
        text=rfm["customer_count"].apply(lambda n: f"{n:,} customers"),
        textposition="outside",
        hovertemplate="<b>%{x}</b><br>Revenue: R$ %{y:,.0f}<br>%{text}<extra></extra>",
    ))
    fig.update_layout(
        title="Revenue by RFM Segment",
        xaxis_title=None, yaxis_title="Total Revenue (R$)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False, height=380,
    )
    st.plotly_chart(fig, use_container_width=True)

with col_right:
    at_risk_rev   = float(kpi_risk["revenue_at_risk"][0])
    total_rev_val = float(totals["total_revenue"][0])
    safe_rev      = total_rev_val - at_risk_rev

    fig2 = go.Figure(go.Pie(
        labels=["Safe Revenue", "Revenue at Risk"],
        values=[safe_rev, at_risk_rev],
        hole=0.55,
        marker_colors=["#2ecc71", "#e74c3c"],
        textinfo="label+percent",
        hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<extra></extra>",
    ))
    fig2.update_layout(
        title="Revenue at Risk (At-Risk + Lost + About to Sleep)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=380,
        annotations=[dict(
            text=f"R$ {at_risk_rev/1e6:.2f}M<br>at risk",
            x=0.5, y=0.5, font_size=14, showarrow=False,
        )],
    )
    st.plotly_chart(fig2, use_container_width=True)

with st.expander("RFM segment detail"):
    display = rfm.copy()
    display.columns = ["Segment", "Customers", "Revenue (R$)", "Avg Revenue", "Avg Recency (days)", "Avg Frequency"]
    st.dataframe(display, use_container_width=True, hide_index=True)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# Section 2 — Delivery Experience
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Delivery Experience & Review Scores")
col_a, col_b = st.columns(2)

with col_a:
    fig3 = go.Figure(go.Bar(
        x=dlv_rev["review_score"],
        y=dlv_rev["avg_delivery_delay_days"],
        name="Avg delay (days)",
        marker_color=["#e74c3c" if v > 0 else "#2ecc71" for v in dlv_rev["avg_delivery_delay_days"]],
        hovertemplate="Score %{x}<br>Avg delay: %{y:.1f} days<extra></extra>",
    ))
    fig3.update_layout(
        title="Avg Delivery Delay by Review Score",
        xaxis_title="Review Score", yaxis_title="Days (negative = arrived early)",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=350, xaxis=dict(tickmode="linear"),
    )
    fig3.add_hline(y=0, line_dash="dash", line_color="grey", line_width=1)
    st.plotly_chart(fig3, use_container_width=True)

with col_b:
    fig4 = go.Figure(go.Bar(
        x=dlv_rev["review_score"],
        y=dlv_rev["late_delivery_pct"],
        marker_color=["#e74c3c" if v > 10 else "#f39c12" if v > 5 else "#2ecc71"
                      for v in dlv_rev["late_delivery_pct"]],
        text=dlv_rev["late_delivery_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        hovertemplate="Score %{x}<br>Late: %{y:.1f}%<extra></extra>",
    ))
    fig4.update_layout(
        title="% of Orders Arriving Late by Review Score",
        xaxis_title="Review Score", yaxis_title="Late Delivery %",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=350, xaxis=dict(tickmode="linear"),
    )
    st.plotly_chart(fig4, use_container_width=True)

st.markdown("**Delivery performance by RFM segment** — do at-risk customers experience worse delivery?")
colors_seg = [SEGMENT_COLORS.get(s, "#95a5a6") for s in seg_dlv["rfm_segment"]]
fig5 = go.Figure()
fig5.add_trace(go.Bar(
    name="Avg delay (days)",
    x=seg_dlv["rfm_segment"],
    y=seg_dlv["avg_delivery_delay_days"],
    marker_color=colors_seg,
    yaxis="y",
    hovertemplate="<b>%{x}</b><br>Avg delay: %{y:.1f} days<extra></extra>",
))
fig5.add_trace(go.Scatter(
    name="Avg review score",
    x=seg_dlv["rfm_segment"],
    y=seg_dlv["avg_review_score"],
    mode="lines+markers",
    marker=dict(size=9, color="#3498db"),
    line=dict(color="#3498db", width=2),
    yaxis="y2",
    hovertemplate="<b>%{x}</b><br>Avg review: %{y:.2f}<extra></extra>",
))
fig5.update_layout(
    title="RFM Segment vs Delivery Delay and Review Score",
    yaxis=dict(title="Avg Delivery Delay (days)"),
    yaxis2=dict(title="Avg Review Score", overlaying="y", side="right", range=[3.5, 4.5]),
    plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
    height=370, legend=dict(orientation="h", y=1.1),
)
fig5.add_hline(y=0, line_dash="dash", line_color="grey", line_width=1)
st.plotly_chart(fig5, use_container_width=True)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# Section 3 — Cohort Retention
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Cohort Retention")
col_coh1, col_coh2 = st.columns([3, 2])

with col_coh1:
    pivot = cohort.pivot(index="cohort_month", columns="period_number", values="retention_pct").fillna(0)
    pivot = pivot.sort_index()
    fig6 = go.Figure(go.Heatmap(
        z=pivot.values,
        x=[f"Month +{c}" for c in pivot.columns],
        y=[str(r) for r in pivot.index],
        colorscale="RdYlGn",
        zmin=0, zmax=100,
        text=[[f"{v:.1f}%" if v > 0 else "" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z:.1f}%<extra></extra>",
    ))
    fig6.update_layout(
        title="Month-over-Month Cohort Retention (%)",
        xaxis_title=None, yaxis_title="Cohort Month",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=420,
    )
    st.plotly_chart(fig6, use_container_width=True)

with col_coh2:
    fig7 = go.Figure(go.Bar(
        x=cohort_avg["period_number"],
        y=cohort_avg["avg_retention_pct"],
        marker_color="#3498db",
        text=cohort_avg["avg_retention_pct"].apply(lambda v: f"{v:.1f}%"),
        textposition="outside",
        hovertemplate="Month +%{x}<br>Avg retention: %{y:.1f}%<extra></extra>",
    ))
    fig7.update_layout(
        title="Avg Retention by Months Since Acquisition",
        xaxis_title="Months Since First Purchase", yaxis_title="Avg Retention %",
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=420, xaxis=dict(tickmode="linear"),
    )
    st.plotly_chart(fig7, use_container_width=True)

st.caption(
    "⚠️ Olist is single-purchase-dominant (~3% repeat rate). "
    "Low retention is a structural finding, not a data issue."
)

st.divider()

# ═════════════════════════════════════════════════════════════════════════════
# Section 4 — Revenue by Category & Geography
# ═════════════════════════════════════════════════════════════════════════════
st.subheader("Revenue by Category & Geography")
col_cat, col_geo = st.columns(2)

with col_cat:
    fig8 = px.bar(
        cat_rev,
        x="total_revenue", y="category_en",
        orientation="h",
        color="avg_delay_days",
        color_continuous_scale="RdYlGn_r",
        labels={"total_revenue": "Revenue (R$)", "category_en": "", "avg_delay_days": "Avg delay (days)"},
        title="Top 15 Categories by Revenue (colour = avg delivery delay)",
        hover_data={"avg_review_score": True, "order_count": True},
    )
    fig8.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=460, yaxis=dict(autorange="reversed"),
        coloraxis_colorbar=dict(title="Delay (days)"),
    )
    st.plotly_chart(fig8, use_container_width=True)

with col_geo:
    fig9 = go.Figure(go.Bar(
        x=state_dlv["avg_delay_days"],
        y=state_dlv["seller_state"],
        orientation="h",
        marker_color=[
            "#e74c3c" if v > 0 else "#f39c12" if v > -5 else "#2ecc71"
            for v in state_dlv["avg_delay_days"]
        ],
        text=state_dlv["avg_review_score"].apply(lambda v: f"★ {v:.2f}"),
        textposition="outside",
        hovertemplate="<b>%{y}</b><br>Avg delay: %{x:.1f} days<br>Review: %{text}<extra></extra>",
    ))
    fig9.add_vline(x=0, line_dash="dash", line_color="grey", line_width=1)
    fig9.update_layout(
        title="Top 20 Seller States by Avg Delivery Delay",
        xaxis_title="Avg Delay (days, negative = early)",
        yaxis_title=None,
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=460, yaxis=dict(autorange="reversed"),
    )
    st.plotly_chart(fig9, use_container_width=True)
