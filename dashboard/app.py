"""
Olist Customer Value Segmentation — Interactive Dashboard
Loads pre-exported parquet files from dashboard/data/
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
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
[data-testid="stMetric"] {
    background: #1e1e2e;
    border-radius: 12px;
    padding: 16px 20px;
    border: 1px solid #313145;
}
[data-testid="stMetricLabel"]  { color: #a0a0b8 !important; font-size: 0.8rem; }
[data-testid="stMetricValue"]  { color: #ffffff !important; font-size: 1.6rem; font-weight: 700; }
[data-testid="stMetricDelta"]  { font-size: 0.8rem; }
.kpi-risk [data-testid="stMetricValue"] { color: #ff6b6b !important; }
div[data-testid="stTabs"] button { font-size: 0.95rem; font-weight: 600; }
</style>
""", unsafe_allow_html=True)

# ── Colour palette ────────────────────────────────────────────────────────────
SEGMENT_COLORS = {
    "Champions":      "#2ecc71",
    "Loyal":          "#27ae60",
    "Promising":      "#3498db",
    "Needs Attention":"#f1c40f",
    "About to Sleep": "#e67e22",
    "At-Risk":        "#e74c3c",
    "Lost":           "#c0392b",
    "Others":         "#95a5a6",
}

# ── Data loading ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).parent / "data"

@st.cache_data
def load(name):
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
scatter_df = load("rfm_scatter")

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📦 Olist Dashboard")
    st.markdown("[🌐 Live App](https://olist-ecom-re.streamlit.app/)  ·  [📂 GitHub](https://github.com/Sayan7anDa5/Olist-ECOM)")
    st.divider()

    st.markdown("### Filters")
    all_segments = rfm["rfm_segment"].tolist()
    selected_segments = st.multiselect(
        "RFM Segments",
        options=all_segments,
        default=all_segments,
        help="Filter charts to specific customer segments",
    )

    top_n_categories = st.slider("Top N categories", min_value=5, max_value=15, value=10)
    top_n_states     = st.slider("Top N states",      min_value=5, max_value=20, value=15)

    st.divider()
    st.caption("Data: Olist Brazilian E-Commerce 2016–2018 · delivered orders only")

# Apply segment filter
rfm_f     = rfm[rfm["rfm_segment"].isin(selected_segments)]
seg_dlv_f = seg_dlv[seg_dlv["rfm_segment"].isin(selected_segments)]
scatter_f = scatter_df[scatter_df["rfm_segment"].isin(selected_segments)]

# ── Header ────────────────────────────────────────────────────────────────────
st.title("📦 Olist Customer Value Segmentation")
st.caption("Olist Brazilian E-Commerce · 2016–2018 · delivered orders only")

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Delivered Orders",     f"{int(totals['total_orders'][0]):,}")
c2.metric("Total Revenue",        f"R$ {int(totals['total_revenue'][0]):,}")
c3.metric("Unique Customers",     f"{int(totals['total_customers'][0]):,}")
c4.metric("Revenue at Risk",      f"{float(kpi_risk['revenue_at_risk_pct'][0]):.1f}%",
          delta=f"R$ {float(kpi_risk['revenue_at_risk'][0]):,.0f}", delta_color="inverse")
c5.metric("Repeat Purchase Rate", f"{float(repeat['repeat_pct'][0]):.1f}%")

st.divider()

# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🏠 Overview", "👥 RFM Segments", "🚚 Delivery & Reviews",
    "🔄 Cohort Retention", "📦 Categories & Geography"
])

# ═════════════════════════════════════════════════════════════════════════════
# Tab 1 — Overview
# ═════════════════════════════════════════════════════════════════════════════
with tab1:
    col_l, col_r = st.columns([3, 2])

    with col_l:
        colors = [SEGMENT_COLORS.get(s, "#95a5a6") for s in rfm_f["rfm_segment"]]
        fig = go.Figure(go.Bar(
            x=rfm_f["rfm_segment"], y=rfm_f["total_revenue"],
            marker_color=colors,
            text=rfm_f["customer_count"].apply(lambda n: f"{n:,}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Revenue: R$ %{y:,.0f}<br>Customers: %{text}<extra></extra>",
        ))
        fig.update_layout(
            title="Revenue by RFM Segment",
            xaxis_title=None, yaxis_title="Total Revenue (R$)",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=380,
            font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig, use_container_width=True)

    with col_r:
        at_risk_rev   = float(kpi_risk["revenue_at_risk"][0])
        total_rev_val = float(totals["total_revenue"][0])
        fig2 = go.Figure(go.Pie(
            labels=["Safe Revenue", "Revenue at Risk"],
            values=[total_rev_val - at_risk_rev, at_risk_rev],
            hole=0.6,
            marker_colors=["#2ecc71", "#e74c3c"],
            textinfo="label+percent",
            hovertemplate="<b>%{label}</b><br>R$ %{value:,.0f}<extra></extra>",
        ))
        fig2.update_layout(
            title="Revenue at Risk",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=380, font=dict(color="#e0e0e0"),
            annotations=[dict(
                text=f"<b>40%</b><br>at risk",
                x=0.5, y=0.5, font_size=16, showarrow=False, font_color="#ff6b6b",
            )],
        )
        st.plotly_chart(fig2, use_container_width=True)

    st.info(
        "**Key findings:** 40% of revenue (R\\$ 6.18M) sits in At-Risk, Lost, and About-to-Sleep segments. "
        "Orders arriving late are **20× more likely** to get a 1-star review. "
        "Only 3% of customers return for a second purchase."
    )

# ═════════════════════════════════════════════════════════════════════════════
# Tab 2 — RFM Deep Dive
# ═════════════════════════════════════════════════════════════════════════════
with tab2:
    col_a, col_b = st.columns(2)

    with col_a:
        colors = [SEGMENT_COLORS.get(s, "#95a5a6") for s in rfm_f["rfm_segment"]]
        fig3 = go.Figure(go.Bar(
            x=rfm_f["rfm_segment"], y=rfm_f["customer_count"],
            marker_color=colors,
            text=rfm_f["customer_count"].apply(lambda n: f"{n:,}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Customers: %{y:,}<extra></extra>",
        ))
        fig3.update_layout(
            title="Customer Count by Segment",
            xaxis_title=None, yaxis_title="Customers",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=360, font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig3, use_container_width=True)

    with col_b:
        fig4 = go.Figure(go.Bar(
            x=rfm_f["rfm_segment"],
            y=rfm_f["avg_revenue_per_customer"],
            marker_color=colors,
            text=rfm_f["avg_revenue_per_customer"].apply(lambda v: f"R$ {v:,.0f}"),
            textposition="outside",
            hovertemplate="<b>%{x}</b><br>Avg spend: R$ %{y:,.0f}<extra></extra>",
        ))
        fig4.update_layout(
            title="Avg Revenue per Customer by Segment",
            xaxis_title=None, yaxis_title="Avg Revenue (R$)",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            showlegend=False, height=360, font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig4, use_container_width=True)

    # RFM Scatter
    st.markdown("##### Recency vs Spend — coloured by segment (sample of 6,000 customers)")
    fig5 = px.scatter(
        scatter_f,
        x="recency_days", y="monetary",
        color="rfm_segment",
        color_discrete_map=SEGMENT_COLORS,
        opacity=0.55,
        labels={"recency_days": "Days Since Last Purchase", "monetary": "Total Spend (R$)", "rfm_segment": "Segment"},
        hover_data={"frequency": True},
        height=420,
    )
    fig5.update_traces(marker=dict(size=5))
    fig5.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e0e0e0"),
        legend=dict(orientation="h", y=-0.2),
    )
    st.plotly_chart(fig5, use_container_width=True)

    # Detail table with download
    with st.expander("Full segment table"):
        display = rfm_f.copy()
        display.columns = ["Segment", "Customers", "Revenue (R$)", "Avg Revenue", "Avg Recency (days)", "Avg Frequency"]
        st.dataframe(display, use_container_width=True, hide_index=True)
        st.download_button(
            "⬇ Download CSV", display.to_csv(index=False),
            file_name="rfm_segments.csv", mime="text/csv",
        )

# ═════════════════════════════════════════════════════════════════════════════
# Tab 3 — Delivery & Reviews
# ═════════════════════════════════════════════════════════════════════════════
with tab3:
    col_a, col_b = st.columns(2)

    with col_a:
        fig6 = go.Figure(go.Bar(
            x=dlv_rev["review_score"],
            y=dlv_rev["avg_delivery_delay_days"],
            marker_color=["#e74c3c" if v > 0 else "#2ecc71" for v in dlv_rev["avg_delivery_delay_days"]],
            text=dlv_rev["avg_delivery_delay_days"].apply(lambda v: f"{v:+.1f}d"),
            textposition="outside",
            hovertemplate="Score %{x}<br>Avg delay: %{y:.1f} days<extra></extra>",
        ))
        fig6.add_hline(y=0, line_dash="dash", line_color="#888", line_width=1)
        fig6.update_layout(
            title="Avg Delivery Delay by Review Score",
            xaxis_title="Review Score", yaxis_title="Days (− = arrived early)",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=360, xaxis=dict(tickmode="linear"), font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig6, use_container_width=True)

    with col_b:
        fig7 = go.Figure(go.Bar(
            x=dlv_rev["review_score"],
            y=dlv_rev["late_delivery_pct"],
            marker_color=["#e74c3c" if v > 10 else "#f39c12" if v > 5 else "#2ecc71"
                          for v in dlv_rev["late_delivery_pct"]],
            text=dlv_rev["late_delivery_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="Score %{x}<br>Late: %{y:.1f}%<br>Orders: %{customdata:,}<extra></extra>",
            customdata=dlv_rev["order_count"],
        ))
        fig7.update_layout(
            title="% Late Deliveries by Review Score",
            xaxis_title="Review Score", yaxis_title="Late Delivery %",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=360, xaxis=dict(tickmode="linear"), font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig7, use_container_width=True)

    st.markdown("##### Delivery experience by RFM segment")
    colors_seg = [SEGMENT_COLORS.get(s, "#95a5a6") for s in seg_dlv_f["rfm_segment"]]
    fig8 = go.Figure()
    fig8.add_trace(go.Bar(
        name="Avg delay (days)",
        x=seg_dlv_f["rfm_segment"], y=seg_dlv_f["avg_delivery_delay_days"],
        marker_color=colors_seg, yaxis="y",
        hovertemplate="<b>%{x}</b><br>Avg delay: %{y:.1f} days<extra></extra>",
    ))
    fig8.add_trace(go.Scatter(
        name="Avg review score",
        x=seg_dlv_f["rfm_segment"], y=seg_dlv_f["avg_review_score"],
        mode="lines+markers",
        marker=dict(size=10, color="#f1c40f", symbol="diamond"),
        line=dict(color="#f1c40f", width=2),
        yaxis="y2",
        hovertemplate="<b>%{x}</b><br>Avg review: %{y:.2f}<extra></extra>",
    ))
    fig8.add_hline(y=0, line_dash="dash", line_color="#888", line_width=1)
    fig8.update_layout(
        yaxis=dict(title="Avg Delay (days)"),
        yaxis2=dict(title="Avg Review Score", overlaying="y", side="right", range=[3.5, 4.5]),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=380, legend=dict(orientation="h", y=1.12),
        font=dict(color="#e0e0e0"),
    )
    st.plotly_chart(fig8, use_container_width=True)

# ═════════════════════════════════════════════════════════════════════════════
# Tab 4 — Cohort Retention
# ═════════════════════════════════════════════════════════════════════════════
with tab4:
    col_a, col_b = st.columns([3, 2])

    with col_a:
        pivot = cohort.pivot(index="cohort_month", columns="period_number", values="retention_pct").fillna(0)
        pivot = pivot.sort_index()
        fig9 = go.Figure(go.Heatmap(
            z=pivot.values,
            x=[f"Month +{c}" for c in pivot.columns],
            y=[str(r) for r in pivot.index],
            colorscale="RdYlGn", zmin=0, zmax=15,
            text=[[f"{v:.1f}%" if v > 0 else "" for v in row] for row in pivot.values],
            texttemplate="%{text}",
            hovertemplate="Cohort: %{y}<br>%{x}<br>Retention: %{z:.1f}%<extra></extra>",
        ))
        fig9.update_layout(
            title="Month-over-Month Cohort Retention (%)",
            xaxis_title=None, yaxis_title="Cohort Month",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=440, font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig9, use_container_width=True)

    with col_b:
        fig10 = go.Figure(go.Bar(
            x=cohort_avg["period_number"],
            y=cohort_avg["avg_retention_pct"],
            marker_color=[
                "#2ecc71" if i == 0 else "#3498db" if v > 3 else "#e74c3c"
                for i, v in enumerate(cohort_avg["avg_retention_pct"])
            ],
            text=cohort_avg["avg_retention_pct"].apply(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="Month +%{x}<br>Avg retention: %{y:.2f}%<extra></extra>",
        ))
        fig10.update_layout(
            title="Avg Retention Rate by Month",
            xaxis_title="Months Since First Purchase", yaxis_title="Avg Retention %",
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=440, xaxis=dict(tickmode="linear"), font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig10, use_container_width=True)

    st.warning("⚠️ Olist is single-purchase-dominant (~3% repeat rate). Low retention is a structural finding of the marketplace model, not a data issue.")

# ═════════════════════════════════════════════════════════════════════════════
# Tab 5 — Categories & Geography
# ═════════════════════════════════════════════════════════════════════════════
with tab5:
    # Treemap
    fig11 = px.treemap(
        cat_rev.head(top_n_categories),
        path=["category_en"],
        values="total_revenue",
        color="avg_delay_days",
        color_continuous_scale="RdYlGn_r",
        color_continuous_midpoint=0,
        title=f"Top {top_n_categories} Categories — size = revenue, colour = avg delivery delay",
        hover_data={"avg_review_score": True, "order_count": True},
    )
    fig11.update_layout(
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        height=400, font=dict(color="#e0e0e0"),
        coloraxis_colorbar=dict(title="Delay (days)"),
    )
    fig11.update_traces(textinfo="label+value+percent root")
    st.plotly_chart(fig11, use_container_width=True)

    col_a, col_b = st.columns(2)

    with col_a:
        cat_slice = cat_rev.head(top_n_categories)
        fig12 = px.bar(
            cat_slice, x="total_revenue", y="category_en", orientation="h",
            color="avg_delay_days", color_continuous_scale="RdYlGn_r",
            labels={"total_revenue": "Revenue (R$)", "category_en": "", "avg_delay_days": "Avg delay (days)"},
            title=f"Top {top_n_categories} Categories by Revenue",
            hover_data={"avg_review_score": ":.2f", "order_count": True},
        )
        fig12.update_layout(
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=420, yaxis=dict(autorange="reversed"),
            font=dict(color="#e0e0e0"),
            coloraxis_colorbar=dict(title="Delay (days)"),
        )
        st.plotly_chart(fig12, use_container_width=True)

    with col_b:
        state_slice = state_dlv.head(top_n_states)
        fig13 = go.Figure(go.Bar(
            x=state_slice["avg_delay_days"], y=state_slice["seller_state"],
            orientation="h",
            marker_color=[
                "#e74c3c" if v > 0 else "#f39c12" if v > -5 else "#2ecc71"
                for v in state_slice["avg_delay_days"]
            ],
            text=state_slice["avg_review_score"].apply(lambda v: f"★ {v:.2f}"),
            textposition="outside",
            hovertemplate="<b>%{y}</b><br>Avg delay: %{x:.1f} days<br>%{text}<extra></extra>",
        ))
        fig13.add_vline(x=0, line_dash="dash", line_color="#888", line_width=1)
        fig13.update_layout(
            title=f"Top {top_n_states} States by Avg Delivery Delay",
            xaxis_title="Avg Delay (days, − = early)", yaxis_title=None,
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            height=420, yaxis=dict(autorange="reversed"),
            font=dict(color="#e0e0e0"),
        )
        st.plotly_chart(fig13, use_container_width=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.caption("🌐 [https://olist-ecom-re.streamlit.app/](https://olist-ecom-re.streamlit.app/)  ·  📂 [GitHub](https://github.com/Sayan7anDa5/Olist-ECOM)  ·  Data: Olist Brazilian E-Commerce 2016–2018")
