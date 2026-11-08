from pathlib import Path

import streamlit as st
import plotly.express as px

from src.analysis import customer_metrics, filter_orders
from src.ui import (
    COLORS,
    apply_theme,
    chart_layout,
    format_brl,
    get_order_facts,
    render_filters,
)


st.set_page_config(page_title="Pelanggan | Sora CRM", layout="wide")
st.logo(
    str(Path(__file__).resolve().parent.parent / "assets" / "sora_logo.svg"),
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

st.caption("CUSTOMER INTELLIGENCE  /  CUSTOMER VALUE")
st.title("Pelanggan & geografi")
st.caption("Peringkat pelanggan menggunakan nilai, frekuensi, dan lokasi pesanan.")
if customers.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

search = st.text_input("Cari ID pelanggan, kota, atau negara bagian")
view = customers
if search:
    mask = (
        view["customer_unique_id"].str.contains(search, case=False, na=False)
        | view["customer_city"].str.contains(search, case=False, na=False)
        | view["customer_state"].str.contains(search, case=False, na=False)
    )
    view = view.loc[mask]

sort_by = st.selectbox(
    "Urutkan pelanggan berdasarkan",
    ["Total belanja", "Jumlah pesanan", "Terakhir bertransaksi"],
)
sort_column = {
    "Total belanja": "total_spent",
    "Jumlah pesanan": "order_count",
    "Terakhir bertransaksi": "last_purchase",
}[sort_by]
table = view.sort_values(sort_column, ascending=False).head(500).copy()
table["total_spent"] = table["total_spent"].map(format_brl)
table["avg_order_value"] = table["avg_order_value"].map(format_brl)
table["last_purchase"] = table["last_purchase"].dt.strftime("%d %b %Y")
table = table.rename(
    columns={
        "customer_unique_id": "ID pelanggan",
        "customer_city": "Kota",
        "customer_state": "Negara bagian",
        "order_count": "Jumlah pesanan",
        "total_spent": "Total belanja",
        "avg_order_value": "Rata-rata pesanan",
        "last_purchase": "Pembelian terakhir",
        "days_since_last": "Hari sejak pembelian",
        "segment": "Segmen",
    }
)
st.dataframe(table, hide_index=True, width="stretch")
st.caption("Tabel menampilkan maksimal 500 baris. Cari untuk mempersempit hasil.")

csv_data = view.to_csv(index=False).encode("utf-8-sig")
st.download_button(
    "Unduh data pelanggan (CSV)",
    data=csv_data,
    file_name="ringkasan_pelanggan_olist.csv",
    mime="text/csv",
)

left, right = st.columns(2)
with left:
    st.subheader("Pelanggan unik per negara bagian")
    by_state = (
        orders.groupby("customer_state", as_index=False)
        .agg(customers=("customer_unique_id", "nunique"))
        .sort_values("customers", ascending=False)
        .head(15)
    )
    figure = px.bar(
        by_state,
        x="customer_state",
        y="customers",
        labels={"customer_state": "Negara bagian", "customers": "Pelanggan unik"},
    )
    figure.update_traces(marker_color=COLORS["terracotta"])
    st.plotly_chart(chart_layout(figure), width="stretch")
with right:
    st.subheader("Kota dengan nilai pesanan tertinggi")
    by_city = (
        orders.groupby("customer_city", as_index=False)
        .agg(revenue=("order_value", "sum"))
        .nlargest(15, "revenue")
        .sort_values("revenue")
    )
    figure = px.bar(
        by_city,
        x="revenue",
        y="customer_city",
        orientation="h",
        labels={"customer_city": "Kota", "revenue": "Nilai pesanan"},
    )
    figure.update_traces(marker_color=COLORS["honey"])
    st.plotly_chart(chart_layout(figure), width="stretch")

st.info(
    "Peringkat pelanggan dihitung dari transaksi terkirim pada rentang filter. "
    "ID yang ditampilkan adalah customer_unique_id agar identitas pelanggan konsisten."
)
