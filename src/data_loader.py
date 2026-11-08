from pathlib import Path

import pandas as pd
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]

CSV_COLUMNS = {
    "olist_customers_dataset.csv": [
        "customer_id",
        "customer_unique_id",
        "customer_city",
        "customer_state",
    ],
    "olist_orders_dataset.csv": [
        "order_id",
        "customer_id",
        "order_status",
        "order_purchase_timestamp",
    ],
    "olist_order_payments_dataset.csv": [
        "order_id",
        "payment_value",
        "payment_type",
    ],
    "olist_order_items_dataset.csv": ["order_id", "product_id", "price"],
    "olist_order_reviews_dataset.csv": ["order_id", "review_score"],
    "olist_products_dataset.csv": ["product_id", "product_category_name"],
    "product_category_name_translation.csv": [
        "product_category_name",
        "product_category_name_english",
    ],
}


@st.cache_data(show_spinner="Memuat dan memeriksa data Olist...")
def load_data() -> dict[str, pd.DataFrame]:
    """Load only the Olist columns used by the dashboard."""
    data: dict[str, pd.DataFrame] = {}
    for filename, columns in CSV_COLUMNS.items():
        path = PROJECT_ROOT / "data" / "raw" / filename
        if not path.is_file():
            raise FileNotFoundError(
                f"File data tidak ditemukan: {path}. "
                "Letakkan file CSV Olist di folder data/raw."
            )
        frame = pd.read_csv(path, usecols=columns)
        missing_columns = set(columns) - set(frame.columns)
        if missing_columns:
            raise ValueError(
                f"Kolom wajib tidak ditemukan di {filename}: "
                f"{', '.join(sorted(missing_columns))}"
            )
        data[filename.removesuffix(".csv")] = frame

    orders = data["olist_orders_dataset"]
    customers = data["olist_customers_dataset"]
    items = data["olist_order_items_dataset"]
    products = data["olist_products_dataset"]

    for name, frame, key in [
        ("pesanan", orders, "order_id"),
        ("pelanggan", customers, "customer_id"),
        ("produk", products, "product_id"),
    ]:
        if frame[key].duplicated().any():
            raise ValueError(f"Kolom {key} pada data {name} harus unik.")

    relationships = [
        ("pesanan → pelanggan", orders["customer_id"], customers["customer_id"]),
        ("item → pesanan", items["order_id"], orders["order_id"]),
        ("item → produk", items["product_id"], products["product_id"]),
    ]
    for relationship, child_keys, parent_keys in relationships:
        missing = child_keys[~child_keys.isin(parent_keys)].nunique()
        if missing:
            raise ValueError(
                f"Relasi {relationship} tidak valid: "
                f"{missing:,} ID tidak memiliki pasangan."
            )

    data["olist_orders_dataset"]["order_purchase_timestamp"] = pd.to_datetime(
        data["olist_orders_dataset"]["order_purchase_timestamp"], errors="coerce"
    )
    if data["olist_orders_dataset"]["order_purchase_timestamp"].isna().any():
        raise ValueError("Ada waktu pembelian yang kosong atau tidak valid.")

    data["olist_products_dataset"] = data["olist_products_dataset"].merge(
        data["product_category_name_translation"],
        on="product_category_name",
        how="left",
        validate="many_to_one",
    )
    product_data = data["olist_products_dataset"]
    product_data["category"] = product_data[
        "product_category_name_english"
    ].fillna(product_data["product_category_name"])
    product_data["category"] = product_data["category"].fillna("Uncategorized")
    return data
