import streamlit as st
import plotly.express as px

from src.analysis import category_metrics, filter_orders
from src.data_loader import load_data
from src.ui import (
    COLORS,
    apply_theme,
    chart_layout,
    get_order_facts,
    render_filters,
)


st.set_page_config(page_title="Produk & strategi | Sora CRM", layout="wide")
apply_theme()
data = load_data()
facts = get_order_facts()
start_date, end_date, states = render_filters(facts)
orders = filter_orders(facts, start_date, end_date, states)

st.caption("CUSTOMER INTELLIGENCE  /  CAMPAIGN OPPORTUNITIES")
st.title("Produk, kepuasan & strategi")
st.caption("Gunakan pola kategori, metode pembayaran, dan ulasan untuk merancang kampanye.")
if orders.empty:
    st.warning("Tidak ada data untuk filter yang dipilih.")
    st.stop()

categories = category_metrics(data, orders)
filter_col, _ = st.columns([1, 2])
with filter_col:
    category_choice = st.selectbox(
        "Tampilkan kategori",
        ["Semua kategori", "10 teratas"],
    )
chart_data = categories.head(10) if category_choice == "10 teratas" else categories.head(20)

left, right = st.columns(2)
with left:
    st.subheader("Nilai item per kategori")
    figure = px.bar(
        chart_data.sort_values("revenue"),
        x="revenue",
        y="category",
        orientation="h",
        labels={"revenue": "Nilai item (R$)", "category": "Kategori"},
    )
    figure.update_traces(marker_color=COLORS["terracotta"])
    st.plotly_chart(chart_layout(figure, height=440), width="stretch")
with right:
    st.subheader("Metode pembayaran")
    payment_orders = orders[["order_id"]].merge(
        data["olist_order_payments_dataset"],
        on="order_id",
        how="inner",
        validate="one_to_many",
    )
    payment_summary = (
        payment_orders.groupby("payment_type", as_index=False)
        .agg(payment_value=("payment_value", "sum"), transactions=("order_id", "nunique"))
        .sort_values("payment_value", ascending=False)
    )
    figure = px.pie(
        payment_summary,
        names="payment_type",
        values="payment_value",
        hole=0.58,
        color_discrete_sequence=[
            COLORS["terracotta"],
            COLORS["sage"],
            COLORS["honey"],
            COLORS["rose"],
            COLORS["taupe"],
        ],
        labels={"payment_type": "Metode pembayaran", "payment_value": "Nilai pembayaran"},
    )
    figure.update_traces(textposition="inside", texttemplate="%{percent:.0%}")
    st.plotly_chart(chart_layout(figure, height=440), width="stretch")

st.subheader("Kepuasan pelanggan")
reviews = orders.loc[orders["review_score"].notna()]
if reviews.empty:
    st.warning("Belum ada ulasan pada filter ini.")
else:
    avg_score = reviews["review_score"].mean()
    positive = reviews["review_score"].ge(4).mean() * 100
    c1, c2, c3 = st.columns(3)
    c1.metric("Rata-rata skor ulasan", f"{avg_score:.2f} / 5")
    c2.metric("Ulasan positif (skor 4–5)", f"{positive:.1f}%")
    c3.metric("Pesanan dengan ulasan", f"{len(reviews):,}".replace(",", "."))

    scores = (
        reviews["review_score"]
        .value_counts()
        .sort_index()
        .rename_axis("score")
        .reset_index(name="reviews")
    )
    figure = px.bar(
        scores,
        x="score",
        y="reviews",
        labels={"score": "Skor ulasan", "reviews": "Jumlah ulasan"},
    )
    figure.update_traces(marker_color=COLORS["sage"])
    st.plotly_chart(chart_layout(figure, height=280), width="stretch")

st.subheader("Rekomendasi pemasaran berbasis data")
top_category = categories.iloc[0]["category"] if not categories.empty else "produk unggulan"
st.markdown(
    f"""
- **Retensi:** prioritaskan pelanggan loyal dan berisiko dengan penawaran yang
  sesuai riwayat pembelian, lalu ukur pembelian ulang.
- **Cross-selling:** uji rekomendasi kategori pendamping untuk pelanggan kategori
  **{top_category}**, dan bandingkan nilai pesanan sebelum/sesudah kampanye.
- **Kepuasan:** evaluasi pesanan dengan skor 1–2 untuk menemukan area perbaikan
  layanan dan pengiriman.
- **Akuisisi geografis:** gunakan negara bagian dengan basis pelanggan terbesar
  sebagai hipotesis untuk uji kampanye regional.
"""
)
st.info(
    "Data Olist tidak memuat sumber akuisisi atau paparan kampanye. "
    "Rekomendasi adalah hipotesis yang perlu diuji, bukan bukti sebab-akibat "
    "atau atribusi kanal pemasaran."
)
