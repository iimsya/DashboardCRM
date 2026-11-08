from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

from src.analysis import SEGMENT_ACTIONS, customer_metrics, filter_orders
from src.ui import (
    COLORS,
    apply_theme,
    chart_layout,
    format_brl,
    get_order_facts,
    render_filters,
)


st.set_page_config(page_title="Loyalitas | Sora CRM", layout="wide")
st.logo(
    str(Path(__file__).resolve().parent.parent / "assets" / "sora_logo.svg"),
    size="large",
)
apply_theme()
facts = get_order_facts()
start_date, end_date, states = render_filters(facts, show_period=False)
orders = filter_orders(facts, start_date, end_date, states)
analysis_date = facts.loc[
    facts["order_status"].eq("delivered"), "order_purchase_timestamp"
].max()
customers = customer_metrics(orders, analysis_date)

st.caption("CUSTOMER INTELLIGENCE  /  RETENTION")
st.title("Loyalitas & risiko pelanggan")
st.caption(
    "Segmentasi ringkas berbasis recency, frequency, dan monetary (RFM). "
    "Pelanggan berisiko ditandai bila pembelian terakhir lebih dari 180 hari lalu."
)
if customers.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

spend_threshold = customers["total_spent"].quantile(0.75)
st.subheader("Cara membaca segmentasi")
st.markdown(
    f"""
- **R (Recency):** tanggal acuan − tanggal pembelian terakhir pelanggan.
  Tanggal acuan data: **{analysis_date:%d %B %Y}**.
- **F (Frequency):** jumlah `order_id` berbeda yang berstatus terkirim.
- **M (Monetary):** total pembayaran (`payment_value`) dari pesanan terkirim.

Nilai ambang **M untuk Champion saat ini: {format_brl(spend_threshold)}**
(persentil ke-75 dari total belanja pelanggan pada filter negara bagian terpilih).
"""
)
segment_rules = pd.DataFrame(
    [
        {
            "Segmen": "Champion",
            "Syarat": (
                "R ≤ 90 hari, F ≥ 2, dan M ≥ "
                f"{format_brl(spend_threshold)} (persentil ke-75)"
            ),
        },
        {
            "Segmen": "Loyal",
            "Syarat": "R ≤ 90 hari, F ≥ 2, dan tidak memenuhi syarat Champion",
        },
        {
            "Segmen": "Potential loyalist",
            "Syarat": "R ≤ 90 hari dan F = 1",
        },
        {
            "Segmen": "At risk",
            "Syarat": "R > 180 hari dan F ≥ 2",
        },
        {
            "Segmen": "Hibernating",
            "Syarat": "Semua pelanggan yang tidak masuk empat segmen di atas",
        },
    ]
)
st.dataframe(segment_rules, hide_index=True, width="stretch")
st.caption(
    "Hibernating adalah kategori sisa: termasuk pelanggan satu kali yang sudah lama "
    "membeli dan pelanggan berulang dengan R 91–180 hari. Ambang hari adalah aturan "
    "analisis tugas ini, bukan label churn yang tercatat di data."
)

segments = (
    customers.groupby("segment", as_index=False)
    .agg(
        customers=("customer_unique_id", "nunique"),
        revenue=("total_spent", "sum"),
        avg_orders=("order_count", "mean"),
    )
)
colors = {
    "Champion": COLORS["terracotta"],
    "Loyal": COLORS["sage"],
    "Potential loyalist": COLORS["honey"],
    "At risk": COLORS["rose"],
    "Hibernating": COLORS["taupe"],
}
figure = px.bar(
    segments.sort_values("customers"),
    x="customers",
    y="segment",
    color="segment",
    orientation="h",
    color_discrete_map=colors,
    labels={"customers": "Pelanggan", "segment": "Segmen"},
)
figure.update_layout(showlegend=False)
st.plotly_chart(chart_layout(figure), width="stretch")

st.subheader("Aksi yang disarankan per segmen")
for segment in ["Champion", "Loyal", "Potential loyalist", "At risk", "Hibernating"]:
    count = int(customers["segment"].eq(segment).sum())
    if count:
        st.markdown(f"**{segment} · {count:,} pelanggan** — {SEGMENT_ACTIONS[segment]}")

at_risk = customers.loc[customers["segment"].eq("At risk")].sort_values(
    ["total_spent", "days_since_last"], ascending=[False, False]
)
st.subheader("Prioritas tindak lanjut: pelanggan berisiko")
if at_risk.empty:
    st.success("Tidak ada pelanggan berisiko pada periode terpilih.")
else:
    risk_table = at_risk.head(100)[
        [
            "customer_unique_id",
            "customer_city",
            "customer_state",
            "order_count",
            "total_spent",
            "days_since_last",
            "avg_review_score",
        ]
    ].copy()
    risk_table["total_spent"] = risk_table["total_spent"].map(format_brl)
    risk_table = risk_table.rename(
        columns={
            "customer_unique_id": "ID pelanggan",
            "customer_city": "Kota",
            "customer_state": "Negara bagian",
            "order_count": "Jumlah pesanan",
            "total_spent": "Total belanja",
            "days_since_last": "Hari tidak bertransaksi",
            "avg_review_score": "Rata-rata ulasan",
        }
    )
    st.dataframe(risk_table, hide_index=True, width="stretch")

st.info(
    f"Tanggal acuan recency adalah pembelian terakhir dalam data terkirim "
    f"({analysis_date:%d %B %Y}), bukan tanggal hari ini. "
    "Threshold 90/180 hari merupakan aturan segmentasi untuk tugas ini, "
    "bukan label churn yang diamati langsung."
)
