from datetime import date

import pandas as pd
import streamlit as st

from src.analysis import build_order_facts
from src.data_loader import load_data

COLORS = {
    "terracotta": "#C86B4A",
    "rose": "#DCA59A",
    "sage": "#A9B7A1",
    "honey": "#E7C98B",
    "charcoal": "#34322E",
    "taupe": "#A39C92",
    "cream": "#F8F5EF",
    "paper": "#FFFDF9",
}

def apply_theme() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700;800&display=swap');
        html, body, [class*="css"], [data-testid="stAppViewContainer"] {
            font-family: 'Manrope', sans-serif;
        }
        [data-testid="stAppViewContainer"] { background: #F8F5EF; }
        [data-testid="stSidebar"] { background: #FFFDF9; border-right: 1px solid #E8DED2; }
        [data-testid="stMetric"] {
            background: #FFFDF9; border: 1px solid #E8DED2; padding: 18px 20px;
            border-radius: 14px; min-height: 112px;
        }
        [data-testid="stMetricLabel"] { color: #777168; }
        [data-testid="stMetricValue"] {
            color: #34322E; font-size: 1.55rem; white-space: nowrap;
        }
        div[data-testid="stPlotlyChart"], div[data-testid="stDataFrame"] {
            background: #FFFDF9; border: 1px solid #E8DED2;
            border-radius: 14px; padding: 8px;
        }
        h1, h2, h3 { color: #34322E; }
        </style>
        """,
        unsafe_allow_html=True,
    )


@st.cache_data(show_spinner="Menyiapkan ringkasan transaksi...")
def get_order_facts() -> pd.DataFrame:
    return build_order_facts(load_data())


def render_filters(
    facts: pd.DataFrame, show_period: bool = True
) -> tuple[date, date, list[str]]:
    with st.sidebar:
        st.markdown("### Filter data")
        min_date = facts["order_purchase_timestamp"].min().date()
        max_date = facts["order_purchase_timestamp"].max().date()
        if show_period:
            dates = st.date_input(
                "Periode pesanan",
                value=(min_date, max_date),
                min_value=min_date,
                max_value=max_date,
                format="DD/MM/YYYY",
            )
            if isinstance(dates, tuple) and len(dates) == 2:
                start_date, end_date = dates
            else:
                start_date = end_date = dates
        else:
            start_date, end_date = min_date, max_date
            st.caption("Segmentasi loyalitas menggunakan seluruh riwayat pesanan.")
        available_states = sorted(facts["customer_state"].dropna().unique().tolist())
        states = st.multiselect("Negara bagian pelanggan", available_states)
        st.divider()
        st.caption(
            "Analisis menggunakan pesanan terkirim. "
            "Data historis Olist berakhir pada 2018."
        )
    return start_date, end_date, states


def format_brl(value: float) -> str:
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def format_brl_compact(value: float) -> str:
    if abs(value) >= 1_000_000:
        return f"R$ {value / 1_000_000:.2f} jt".replace(".", ",")
    if abs(value) >= 10_000:
        return f"R$ {value / 1_000:.1f} rb".replace(".", ",")
    return format_brl(value)


def chart_layout(fig, height: int = 340):
    fig.update_layout(
        height=height,
        margin=dict(l=12, r=12, t=42, b=12),
        paper_bgcolor=COLORS["paper"],
        plot_bgcolor=COLORS["paper"],
        font=dict(family="Manrope, sans-serif", color=COLORS["charcoal"]),
        legend=dict(orientation="h", y=1.12, x=0),
    )
    fig.update_xaxes(showgrid=False, linecolor="#E8DED2")
    fig.update_yaxes(gridcolor="#EEE7DE", zerolinecolor="#EEE7DE")
    return fig
