import unittest

import pandas as pd

from src.analysis import build_order_facts, customer_metrics, filter_orders


class AnalysisTests(unittest.TestCase):
    def setUp(self):
        self.data = {
            "olist_orders_dataset": pd.DataFrame(
                {
                    "order_id": ["o1", "o2"],
                    "customer_id": ["c1", "c2"],
                    "order_status": ["delivered", "delivered"],
                    "order_purchase_timestamp": pd.to_datetime(
                        ["2018-01-01", "2018-01-02"]
                    ),
                }
            ),
            "olist_customers_dataset": pd.DataFrame(
                {
                    "customer_id": ["c1", "c2"],
                    "customer_unique_id": ["u1", "u1"],
                    "customer_city": ["city", "city"],
                    "customer_state": ["SP", "SP"],
                }
            ),
            "olist_order_payments_dataset": pd.DataFrame(
                {
                    "order_id": ["o1", "o1", "o2"],
                    "payment_value": [30.0, 20.0, 40.0],
                }
            ),
            "olist_order_items_dataset": pd.DataFrame(
                {
                    "order_id": ["o1", "o1", "o2"],
                    "product_id": ["p1", "p2", "p1"],
                    "price": [25.0, 25.0, 40.0],
                }
            ),
            "olist_order_reviews_dataset": pd.DataFrame(
                {"order_id": ["o1"], "review_score": [5]}
            ),
        }

    def test_order_facts_aggregate_to_one_row_without_multiplying_values(self):
        facts = build_order_facts(self.data)
        self.assertEqual(len(facts), 2)
        first_order = facts.set_index("order_id").loc["o1"]
        self.assertEqual(first_order["order_value"], 50.0)
        self.assertEqual(first_order["item_value"], 50.0)
        self.assertEqual(first_order["item_count"], 2)

    def test_customer_metrics_use_unique_customer_id_and_sum_orders(self):
        facts = build_order_facts(self.data)
        orders = filter_orders(
            facts, pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-02")
        )
        customers = customer_metrics(orders, pd.Timestamp("2018-01-02"))
        self.assertEqual(len(customers), 1)
        self.assertEqual(customers.iloc[0]["customer_unique_id"], "u1")
        self.assertEqual(customers.iloc[0]["order_count"], 2)
        self.assertEqual(customers.iloc[0]["total_spent"], 90.0)

    def test_order_filter_excludes_non_delivered_orders(self):
        facts = build_order_facts(self.data)
        facts.loc[facts["order_id"].eq("o2"), "order_status"] = "canceled"
        orders = filter_orders(
            facts, pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-02")
        )
        self.assertEqual(orders["order_id"].tolist(), ["o1"])

    def test_repeat_customer_becomes_at_risk_after_180_days(self):
        facts = build_order_facts(self.data)
        facts["order_purchase_timestamp"] = pd.to_datetime(
            ["2017-01-01", "2017-01-02"]
        )
        orders = filter_orders(
            facts, pd.Timestamp("2017-01-01"), pd.Timestamp("2017-01-02")
        )
        customers = customer_metrics(orders, pd.Timestamp("2018-01-02"))
        self.assertEqual(customers.iloc[0]["days_since_last"], 365)
        self.assertEqual(customers.iloc[0]["segment"], "At risk")

    def test_customer_location_keeps_mode_when_addresses_differ(self):
        facts = build_order_facts(self.data)
        facts = pd.concat([facts, facts.loc[facts["order_id"].eq("o2")]], ignore_index=True)
        facts.loc[facts.index == 2, "order_id"] = "o3"
        facts.loc[facts.index == 2, "customer_city"] = "other city"
        facts.loc[facts.index == 2, "customer_state"] = "RJ"
        facts.loc[facts.index == 2, "order_purchase_timestamp"] = pd.Timestamp(
            "2018-01-03"
        )
        orders = filter_orders(
            facts, pd.Timestamp("2018-01-01"), pd.Timestamp("2018-01-03")
        )
        customers = customer_metrics(orders, pd.Timestamp("2018-01-03"))
        self.assertEqual(customers.iloc[0]["customer_city"], "city")
        self.assertEqual(customers.iloc[0]["customer_state"], "SP")


if __name__ == "__main__":
    unittest.main()
