import pandas as pd
import streamlit as st


def build_order_facts(data: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Build one row per order to avoid multiplying payment and item values."""
    orders = data["olist_orders_dataset"].copy()
    customers = data["olist_customers_dataset"][
        ["customer_id", "customer_unique_id", "customer_city", "customer_state"]
    ]
    payments = (
        data["olist_order_payments_dataset"]
        .groupby("order_id", as_index=False)
        .agg(order_value=("payment_value", "sum"))
    )
    items = (
        data["olist_order_items_dataset"]
        .groupby("order_id", as_index=False)
        .agg(item_value=("price", "sum"), item_count=("product_id", "size"))
    )
    reviews = (
        data["olist_order_reviews_dataset"]
        .groupby("order_id", as_index=False)
        .agg(review_score=("review_score", "mean"))
    )
    facts = (
        orders.merge(customers, on="customer_id", how="left", validate="many_to_one")
        .merge(payments, on="order_id", how="left", validate="one_to_one")
        .merge(items, on="order_id", how="left", validate="one_to_one")
        .merge(reviews, on="order_id", how="left", validate="one_to_one")
    )
    facts["order_value"] = facts["order_value"].fillna(0)
    facts["item_value"] = facts["item_value"].fillna(0)
    facts["item_count"] = facts["item_count"].fillna(0).astype("int64")
    return facts


def filter_orders(
    facts: pd.DataFrame,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    states: list[str] | None = None,
) -> pd.DataFrame:
    purchase_time = facts["order_purchase_timestamp"]
    selected = facts.loc[
        facts["order_status"].eq("delivered")
        & purchase_time.ge(pd.Timestamp(start_date))
        & purchase_time.lt(pd.Timestamp(end_date) + pd.Timedelta(days=1))
    ]
    if states:
        selected = selected.loc[selected["customer_state"].isin(states)]
    return selected.copy()


@st.cache_data(show_spinner=False)
def customer_metrics(orders: pd.DataFrame, analysis_date: pd.Timestamp) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(
            columns=[
                "customer_unique_id",
                "customer_city",
                "customer_state",
                "order_count",
                "total_spent",
                "avg_order_value",
                "last_purchase",
                "first_purchase",
                "avg_review_score",
                "days_since_last",
                "segment",
            ]
        )
    location_modes = {}
    for column in ["customer_city", "customer_state"]:
        counts = (
            orders.groupby(["customer_unique_id", column], dropna=False)
            .size()
            .rename("count")
            .reset_index()
            .sort_values(
                ["customer_unique_id", "count", column],
                ascending=[True, False, True],
                kind="stable",
            )
            .drop_duplicates("customer_unique_id")
            .set_index("customer_unique_id")[column]
        )
        location_modes[column] = counts

    customers = orders.groupby("customer_unique_id", as_index=False).agg(
        order_count=("order_id", "nunique"),
        total_spent=("order_value", "sum"),
        avg_order_value=("order_value", "mean"),
        last_purchase=("order_purchase_timestamp", "max"),
        first_purchase=("order_purchase_timestamp", "min"),
        avg_review_score=("review_score", "mean"),
    )
    for column, modes in location_modes.items():
        customers[column] = customers["customer_unique_id"].map(modes)
    customers["days_since_last"] = (
        pd.Timestamp(analysis_date).normalize()
        - customers["last_purchase"].dt.normalize()
    ).dt.days

    high_value = customers["total_spent"].ge(customers["total_spent"].quantile(0.75))
    recent = customers["days_since_last"].le(90)
    repeat = customers["order_count"].ge(2)
    customers["segment"] = "Hibernating"
    customers.loc[customers["days_since_last"].gt(180) & repeat, "segment"] = (
        "At risk"
    )
    customers.loc[recent & repeat, "segment"] = "Loyal"
    customers.loc[recent & repeat & high_value, "segment"] = "Champion"
    customers.loc[recent & ~repeat, "segment"] = "Potential loyalist"
    return customers


def category_metrics(
    data: dict[str, pd.DataFrame], orders: pd.DataFrame
) -> pd.DataFrame:
    if orders.empty:
        return pd.DataFrame(columns=["category", "revenue", "items_sold"])
    order_ids = orders["order_id"]
    products = data["olist_products_dataset"][["product_id", "category"]]
    lines = data["olist_order_items_dataset"].loc[
        data["olist_order_items_dataset"]["order_id"].isin(order_ids)
    ]
    return (
        lines.merge(products, on="product_id", how="left", validate="many_to_one")
        .groupby("category", as_index=False)
        .agg(revenue=("price", "sum"), items_sold=("product_id", "size"))
        .sort_values("revenue", ascending=False)
    )


SEGMENT_ACTIONS = {
    "Champion": "Pertahankan dengan layanan premium, program referral, dan apresiasi loyalitas.",
    "Loyal": "Berikan reward pembelian berulang dan rekomendasi produk terkait.",
    "Potential loyalist": "Dorong pesanan kedua dengan penawaran relevan dan edukasi produk.",
    "At risk": "Lakukan kampanye win-back dan pantau respons serta ulasan pelanggan.",
    "Hibernating": "Uji kampanye reaktivasi berbiaya rendah; evaluasi hasil sebelum diskalakan.",
}
