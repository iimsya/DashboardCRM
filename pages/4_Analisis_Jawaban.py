import pandas as pd
import plotly.express as px
import streamlit as st

from src.analysis import (
    SEGMENT_ACTIONS,
    category_metrics,
    customer_metrics,
    filter_orders,
)
from src.data_loader import load_data
from src.ui import (
    COLORS,
    apply_theme,
    chart_layout,
    format_brl,
    format_brl_compact,
    get_order_facts,
    render_filters,
)


st.set_page_config(page_title="Analisis & jawaban | Sora CRM", layout="wide")
apply_theme()

data = load_data()
facts = get_order_facts()
start_date, end_date, states = render_filters(facts)
orders = filter_orders(facts, start_date, end_date, states)
all_delivered = filter_orders(
    facts,
    facts["order_purchase_timestamp"].min(),
    facts["order_purchase_timestamp"].max(),
    states,
)
analysis_date = facts.loc[
    facts["order_status"].eq("delivered"), "order_purchase_timestamp"
].max()
customers = customer_metrics(orders, analysis_date)
full_history_customers = customer_metrics(all_delivered, analysis_date)

st.caption("CUSTOMER INTELLIGENCE  /  BUSINESS ANSWERS")
st.title("Analisis & jawaban CRM")
st.caption(
    "Jawaban berbasis pesanan terkirim, dengan bukti angka, tabel, dan grafik. "
    "Gunakan filter di sidebar untuk mengubah periode dan wilayah."
)
if orders.empty or customers.empty:
    st.warning("Tidak ada pesanan terkirim untuk filter yang dipilih.")
    st.stop()

st.caption(
    f"Periode transaksi terpilih: **{start_date:%d %b %Y} – {end_date:%d %b %Y}**. "
    f"Risiko dan loyalitas memakai seluruh riwayat sampai **{analysis_date:%d %b %Y}**."
)

st.header("1. Siapa pelanggan terbaik?")
top_customers = customers.nlargest(10, "total_spent").copy()
top_customer = top_customers.iloc[0]
st.markdown(
    f"**Jawaban:** pelanggan dengan nilai belanja tertinggi pada filter saat ini "
    f"membelanjakan **{format_brl(top_customer['total_spent'])}** dari "
    f"{int(top_customer['order_count'])} pesanan terkirim."
)
left, right = st.columns([1.2, 1])
with left:
    figure = px.bar(
        top_customers.sort_values("total_spent"),
        x="total_spent",
        y="customer_unique_id",
        orientation="h",
        labels={"total_spent": "Total belanja (R$)", "customer_unique_id": "ID pelanggan"},
    )
    figure.update_traces(marker_color=COLORS["terracotta"])
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_best_customers")
with right:
    evidence = top_customers[
        ["customer_unique_id", "customer_city", "customer_state", "order_count", "total_spent"]
    ].copy()
    evidence["total_spent"] = evidence["total_spent"].map(format_brl)
    evidence = evidence.rename(
        columns={
            "customer_unique_id": "ID pelanggan",
            "customer_city": "Kota",
            "customer_state": "Negara bagian",
            "order_count": "Pesanan",
            "total_spent": "Total belanja",
        }
    )
    st.dataframe(evidence, hide_index=True, width="stretch", key="answer_best_customer_table")
st.caption(
    "Peringkat ditentukan dari total pembayaran pesanan terkirim per "
    "`customer_unique_id`; pelanggan tidak dihitung ganda karena memiliki beberapa customer_id."
)

st.header("2. Dari mana pelanggan berasal?")
state_customers = (
    orders.groupby("customer_state", as_index=False)
    .agg(
        customers=("customer_unique_id", "nunique"),
        revenue=("order_value", "sum"),
    )
    .sort_values("customers", ascending=False)
)
leading_state = state_customers.iloc[0]
st.markdown(
    f"**Jawaban:** negara bagian dengan pelanggan terbanyak adalah "
    f"**{leading_state['customer_state']}**, dengan "
    f"**{int(leading_state['customers']):,} pelanggan unik** dan nilai pembayaran "
    f"**{format_brl(leading_state['revenue'])}** pada periode terpilih."
)
left, right = st.columns(2)
with left:
    figure = px.bar(
        state_customers.head(12).sort_values("customers"),
        x="customers",
        y="customer_state",
        orientation="h",
        labels={"customers": "Pelanggan unik", "customer_state": "Negara bagian"},
    )
    figure.update_traces(marker_color=COLORS["sage"])
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_customer_state_count")
with right:
    figure = px.bar(
        state_customers.nlargest(12, "revenue").sort_values("revenue"),
        x="revenue",
        y="customer_state",
        orientation="h",
        labels={"revenue": "Nilai pembayaran (R$)", "customer_state": "Negara bagian"},
    )
    figure.update_traces(marker_color=COLORS["honey"])
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_state_revenue")
st.caption("Lokasi berasal dari alamat pelanggan di data Olist, bukan sumber kanal pemasaran.")

st.header("3. Berapa nilai transaksi setiap pelanggan?")
st.markdown(
    "**Jawaban:** total transaksi pelanggan dihitung sebagai jumlah `payment_value` "
    "dari pesanan terkirim miliknya. Rata-rata transaksi adalah total tersebut dibagi "
    "jumlah pesanan terkirim."
)
value_view = customers.sort_values("total_spent", ascending=False).copy()
value_view["avg_order_value"] = value_view["avg_order_value"].map(format_brl)
value_view["total_spent"] = value_view["total_spent"].map(format_brl)
value_table = value_view[
    [
        "customer_unique_id",
        "customer_city",
        "customer_state",
        "order_count",
        "total_spent",
        "avg_order_value",
    ]
].rename(
    columns={
        "customer_unique_id": "ID pelanggan",
        "customer_city": "Kota",
        "customer_state": "Negara bagian",
        "order_count": "Jumlah pesanan",
        "total_spent": "Total transaksi",
        "avg_order_value": "Rata-rata per pesanan",
    }
)
st.dataframe(
    value_table.head(100),
    hide_index=True,
    width="stretch",
    key="answer_customer_values_table",
)
st.download_button(
    "Unduh nilai transaksi semua pelanggan (CSV)",
    data=value_view.to_csv(index=False).encode("utf-8-sig"),
    file_name="nilai_transaksi_pelanggan_olist.csv",
    mime="text/csv",
)
figure = px.histogram(
    customers,
    x="total_spent",
    nbins=40,
    labels={"total_spent": "Total transaksi per pelanggan (R$)", "count": "Pelanggan"},
)
figure.update_traces(marker_color=COLORS["terracotta"])
st.plotly_chart(chart_layout(figure), width="stretch", key="answer_customer_value_distribution")
st.caption("Grafik distribusi memperlihatkan konsentrasi pelanggan menurut total belanja; tabel menampilkan 100 teratas.")

st.header("4. Pelanggan mana yang berpotensi tidak aktif?")
risk_counts = (
    full_history_customers["segment"]
    .value_counts()
    .reindex(
        ["At risk", "Hibernating", "Potential loyalist", "Loyal", "Champion"],
        fill_value=0,
    )
    .rename_axis("segment")
    .reset_index(name="customers")
)
at_risk_count = int(risk_counts.loc[risk_counts["segment"].eq("At risk"), "customers"].iloc[0])
at_risk_customers = full_history_customers.loc[
    full_history_customers["segment"].eq("At risk")
].sort_values(["total_spent", "days_since_last"], ascending=[False, False])
st.markdown(
    f"**Jawaban:** terdapat **{at_risk_count:,} pelanggan berisiko** menurut aturan "
    "dashboard: memiliki minimal dua pesanan terkirim dan sudah lebih dari 180 hari "
    "tidak bertransaksi, dihitung sampai akhir riwayat data."
)
left, right = st.columns([1, 1.3])
with left:
    figure = px.bar(
        risk_counts.sort_values("customers"),
        x="customers",
        y="segment",
        color="segment",
        orientation="h",
        color_discrete_map={
            "Champion": COLORS["terracotta"],
            "Loyal": COLORS["sage"],
            "Potential loyalist": COLORS["honey"],
            "At risk": COLORS["rose"],
            "Hibernating": COLORS["taupe"],
        },
        labels={"customers": "Pelanggan", "segment": "Segmen"},
    )
    figure.update_layout(showlegend=False)
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_risk_segments")
with right:
    risk_table = at_risk_customers.head(20)[
        [
            "customer_unique_id",
            "customer_state",
            "order_count",
            "total_spent",
            "days_since_last",
        ]
    ].copy()
    risk_table["total_spent"] = risk_table["total_spent"].map(format_brl)
    risk_table = risk_table.rename(
        columns={
            "customer_unique_id": "ID pelanggan",
            "customer_state": "Negara bagian",
            "order_count": "Pesanan",
            "total_spent": "Total belanja",
            "days_since_last": "Hari tidak aktif",
        }
    )
    st.dataframe(risk_table, hide_index=True, width="stretch", key="answer_at_risk_table")
st.caption(
    f"Tanggal acuan adalah {analysis_date:%d %b %Y}. Dataset berakhir pada 2018; "
    "ini menunjukkan risiko relatif terhadap riwayat tersebut, bukan status pelanggan saat ini. "
    "Hibernating merupakan kategori sisa, bukan semua pelanggan yang pasti churn."
)

st.header("5. Bagaimana perusahaan meningkatkan loyalitas pelanggan?")
segment_summary = (
    full_history_customers.groupby("segment", as_index=False)
    .agg(
        customers=("customer_unique_id", "nunique"),
        revenue=("total_spent", "sum"),
        avg_review=("avg_review_score", "mean"),
    )
)
segment_summary["share"] = segment_summary["customers"] / len(full_history_customers) * 100
st.markdown(
    "**Jawaban:** terapkan program berbeda menurut tahap hubungan pelanggan—"
    "pertahankan pelanggan terbaik, dorong pembelian kedua, dan lakukan win-back "
    "untuk pelanggan berisiko."
)
left, right = st.columns(2)
with left:
    figure = px.bar(
        segment_summary.sort_values("customers"),
        x="customers",
        y="segment",
        color="segment",
        orientation="h",
        color_discrete_map={
            "Champion": COLORS["terracotta"],
            "Loyal": COLORS["sage"],
            "Potential loyalist": COLORS["honey"],
            "At risk": COLORS["rose"],
            "Hibernating": COLORS["taupe"],
        },
        labels={"customers": "Pelanggan", "segment": "Segmen"},
    )
    figure.update_layout(showlegend=False)
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_loyalty_segments")
with right:
    loyalty_evidence = segment_summary.copy()
    loyalty_evidence["share"] = loyalty_evidence["share"].map(lambda v: f"{v:.1f}%")
    loyalty_evidence["revenue"] = loyalty_evidence["revenue"].map(format_brl_compact)
    loyalty_evidence["avg_review"] = loyalty_evidence["avg_review"].map(
        lambda value: f"{value:.2f} / 5" if pd.notna(value) else "Belum ada ulasan"
    )
    loyalty_evidence = loyalty_evidence.rename(
        columns={
            "segment": "Segmen",
            "customers": "Pelanggan",
            "share": "Porsi pelanggan",
            "revenue": "Total belanja",
            "avg_review": "Rata-rata ulasan",
        }
    )
    st.dataframe(loyalty_evidence, hide_index=True, width="stretch", key="answer_loyalty_evidence")

loyalty_actions = pd.DataFrame(
    [{"Segmen": segment, "Aksi CRM": SEGMENT_ACTIONS[segment]} for segment in [
        "Champion",
        "Loyal",
        "Potential loyalist",
        "At risk",
        "Hibernating",
    ]]
)
st.dataframe(
    loyalty_actions,
    hide_index=True,
    width="stretch",
    key="answer_loyalty_actions",
)
st.caption(
    "Jumlah dan nilai segmen menggunakan seluruh pesanan terkirim. "
    "Ulasan rata-rata hanya dihitung dari pesanan yang memiliki skor ulasan."
)

st.header("6. Strategi pemasaran apa yang harus diterapkan?")
strategy_categories = category_metrics(data, orders)
top_category = strategy_categories.iloc[0] if not strategy_categories.empty else None
top_state_revenue = state_customers.iloc[state_customers["revenue"].argmax()]
if top_category is not None:
    st.markdown(
        f"**Bukti:** kategori dengan nilai item tertinggi adalah "
        f"**{top_category['category']}** "
        f"({format_brl(top_category['revenue'])}); wilayah dengan nilai pembayaran "
        f"terbesar adalah **{top_state_revenue['customer_state']}** "
        f"({format_brl(top_state_revenue['revenue'])})."
    )
left, right = st.columns(2)
with left:
    figure = px.bar(
        strategy_categories.head(10).sort_values("revenue"),
        x="revenue",
        y="category",
        orientation="h",
        labels={"revenue": "Nilai item (R$)", "category": "Kategori"},
    )
    figure.update_traces(marker_color=COLORS["terracotta"])
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_top_categories")
with right:
    figure = px.bar(
        state_customers.nlargest(10, "revenue").sort_values("revenue"),
        x="revenue",
        y="customer_state",
        orientation="h",
        labels={"revenue": "Nilai pembayaran (R$)", "customer_state": "Negara bagian"},
    )
    figure.update_traces(marker_color=COLORS["sage"])
    st.plotly_chart(chart_layout(figure), width="stretch", key="answer_marketing_regions")

st.markdown(
    """
- **Retensi & win-back:** prioritaskan segmen At risk dengan riwayat belanja tinggi;
  uji penawaran terbatas dan ukur tingkat pembelian ulang.
- **Pembelian kedua:** kirim rekomendasi produk relevan kepada Potential loyalist
  setelah pesanan pertama diterima.
- **Loyalitas & referral:** beri benefit bertingkat kepada Loyal dan Champion,
  lalu pantau frekuensi pesanan dan nilai pelanggan.
- **Cross-selling:** uji produk pelengkap pada kategori terlaris dan bandingkan
  rata-rata nilai pesanan kelompok uji dengan kelompok pembanding.
- **Eksperimen regional:** uji kampanye di negara bagian dengan basis pelanggan
  atau nilai pembayaran tinggi; evaluasi konversi sebelum memperluas anggaran.
"""
)
st.info(
    "Dataset tidak mencatat kanal akuisisi, paparan iklan, atau hasil kampanye. "
    "Karena itu rekomendasi di atas adalah hipotesis untuk diuji; data lokasi dan "
    "kategori tidak membuktikan kanal pemasaran atau sebab-akibat."
)
