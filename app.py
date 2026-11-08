from pathlib import Path

import plotly.express as px
import streamlit as st

from src.analysis import customer_metrics, filter_orders
from src.ui import (
    COLORS,
    apply_theme,
    chart_layout,
    format_brl,
    format_brl_compact,
    get_order_facts,
    render_filters,
)


st.set_page_config(
    page_title="Sora | CRM Dashboard",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)
st.logo(
    str(Path(__file__).resolve().parent / "assets" / "sora_logo.svg"),
    size="large",
)
apply_theme()

facts = get_order_facts()
start_date, end_date, states = render_filters(facts)
orders = filter_orders(facts, start_date, end_date, states)
analysis_date = facts.loc[
    facts["order_status"].eq("delivered"), "order_purchase_timestamp"
].max()
customers = customer_metrics(orders, analysis_date)

st.caption("CUSTOMER INTELLIGENCE  /  OVERVIEW")
st.title("Ringkasan pelanggan")
st.caption("Pantau nilai pelanggan, pola transaksi, dan peluang retensi.")

if orders.empty:
    st.warning("Tidak ada pesanan terkirim untuk filter yang dipilih.")
    st.stop()

repeat_customers = int(customers["order_count"].ge(2).sum())
repeat_rate = repeat_customers / len(customers) * 100
total_revenue = orders["order_value"].sum()
average_order = orders["order_value"].mean()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Pelanggan unik", f"{len(customers):,}".replace(",", "."))
col2.metric(
    "Pelanggan berulang",
    f"{repeat_customers:,}".replace(",", "."),
    f"{repeat_rate:.1f}% dari pelanggan",
)
col3.metric("Nilai pesanan terkirim", format_brl_compact(total_revenue))
col4.metric("Rata-rata nilai pesanan", format_brl_compact(average_order))

monthly = (
    orders.assign(month=orders["order_purchase_timestamp"].dt.to_period("M").dt.to_timestamp())
    .groupby("month", as_index=False)
    .agg(revenue=("order_value", "sum"), orders=("order_id", "nunique"))
)
left, right = st.columns([1.7, 1])
with left:
    st.subheader("Tren nilai pesanan")
    figure = px.line(
        monthly,
        x="month",
        y="revenue",
        markers=True,
        labels={"month": "Bulan", "revenue": "Nilai pesanan"},
    )
    figure.update_traces(line_color=COLORS["terracotta"], marker_color=COLORS["terracotta"])
    st.plotly_chart(chart_layout(figure), width="stretch")
with right:
    st.subheader("Pelanggan menurut segmen")
    segment_counts = (
        customers["segment"].value_counts().rename_axis("segment").reset_index(name="customers")
    )
    segment_colors = {
        "Champion": COLORS["terracotta"],
        "Loyal": COLORS["sage"],
        "Potential loyalist": COLORS["honey"],
        "At risk": COLORS["rose"],
        "Hibernating": COLORS["taupe"],
    }
    figure = px.pie(
        segment_counts,
        names="segment",
        values="customers",
        hole=0.62,
        color="segment",
        color_discrete_map=segment_colors,
    )
    figure.update_traces(textposition="inside", texttemplate="%{percent:.0%}")
    st.plotly_chart(chart_layout(figure), width="stretch")

left, right = st.columns([1.2, 1])
with left:
    st.subheader("Asal pelanggan")
    by_state = (
        orders.groupby("customer_state", as_index=False)
        .agg(customers=("customer_unique_id", "nunique"), revenue=("order_value", "sum"))
        .sort_values("customers", ascending=False)
        .head(12)
        .sort_values("customers")
    )
    figure = px.bar(
        by_state,
        x="customers",
        y="customer_state",
        orientation="h",
        labels={"customers": "Pelanggan unik", "customer_state": "Negara bagian"},
    )
    figure.update_traces(marker_color=COLORS["sage"])
    st.plotly_chart(chart_layout(figure), width="stretch")
with right:
    st.subheader("Pelanggan bernilai tertinggi")
    best = customers.nlargest(10, "total_spent")[
        [
            "customer_unique_id",
            "customer_city",
            "customer_state",
            "order_count",
            "total_spent",
            "segment",
        ]
    ].copy()
    best["total_spent"] = best["total_spent"].map(format_brl)
    st.dataframe(best, hide_index=True, width="stretch")

st.info(
    "Nilai transaksi berasal dari total pembayaran pesanan berstatus terkirim. "
    "Dataset tidak mencatat kanal pemasaran, sehingga asal pelanggan di sini "
    "berarti lokasi geografis, bukan sumber iklan."
)
