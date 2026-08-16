"""
Customer order + SKU + quantity forecasting.

For each customer: predicts whether they'll order on a given day, which
items they're likely to order, and in what quantity, then aggregates
those predictions into warehouse-level SKU demand.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import ast
import numpy as np
import pandas as pd
from lightgbm import LGBMClassifier
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import StratifiedKFold, cross_val_score, train_test_split
from sklearn.preprocessing import LabelEncoder


@dataclass
class ForecastConfig:
    order_threshold: float = 0.20
    random_state: int = 42
    n_estimators: int = 200
    order_max_depth: int = 7
    item_max_depth: int = 10
    quantity_max_depth: int = 10
    stochastic_item_count: bool = False


FEATURES = [
    "day_name_encoded",
    "days_since_first_order",
    "ordered_yesterday",
    "order_frequency",
    "total_orders",
    "day_of_week_encoded",
    "month_encoded",
    "week_of_year_encoded",
]


def validate_orders(df: pd.DataFrame) -> None:
    required = {"customer_id", "order_date", "item_name", "quantity"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing required order columns: {sorted(missing)}")


def build_encoders():
    day_encoder = LabelEncoder()
    day_encoder.fit(
        ["Monday", "Tuesday", "Wednesday", "Thursday",
         "Friday", "Saturday", "Sunday"]
    )

    dow = LabelEncoder()
    dow.fit(range(7))

    month = LabelEncoder()
    month.fit(range(1, 13))

    week = LabelEncoder()
    week.fit(range(1, 54))

    return day_encoder, dow, month, week


def customer_history(customer_data: pd.DataFrame, start_date: pd.Timestamp):
    customer_data = customer_data.copy()
    customer_data["order_date"] = pd.to_datetime(customer_data["order_date"])

    first_order = (
        customer_data["order_date"].min()
        if not customer_data.empty
        else start_date
    )

    dates = pd.date_range(
        start=customer_data["order_date"].min()
        if not customer_data.empty else start_date,
        end=customer_data["order_date"].max()
        if not customer_data.empty else start_date,
        freq="D",
    )

    order_dates = set(customer_data["order_date"].dt.normalize())
    order_freq = (
        customer_data["order_date"].nunique()
        / max((customer_data["order_date"].max()
               - customer_data["order_date"].min()).days + 1, 1)
        if not customer_data.empty else 0.0
    )
    total_orders = (
        customer_data["order_date"].nunique()
        if not customer_data.empty else 0
    )

    hist = pd.DataFrame({"date": dates})
    hist["day_name"] = hist["date"].dt.day_name()
    hist["ordered"] = hist["date"].isin(order_dates).astype(int)
    hist["order_frequency"] = order_freq
    hist["total_orders"] = total_orders
    hist["day_of_week"] = hist["date"].dt.weekday
    hist["month"] = hist["date"].dt.month
    hist["week_of_year"] = hist["date"].dt.isocalendar().week.astype(int)
    hist["days_since_first_order"] = (hist["date"] - first_order).dt.days
    hist["ordered_yesterday"] = hist["ordered"].shift(1).fillna(0)

    return customer_data, hist, first_order, order_freq, total_orders


def encode_features(df, encoders):
    day_encoder, dow, month, week = encoders
    x = df.copy()
    x["day_name_encoded"] = day_encoder.transform(x["day_name"])
    x["day_of_week_encoded"] = dow.transform(x["day_of_week"].astype(int))
    x["month_encoded"] = month.transform(x["month"].astype(int))
    x["week_of_year_encoded"] = week.transform(x["week_of_year"].astype(int))
    return x


def train_order_model(hist: pd.DataFrame, config: ForecastConfig):
    x = hist.copy()
    encoders = build_encoders()
    x = encode_features(x, encoders)

    X = x[FEATURES]
    y = x["ordered"]

    if len(X) < 4 or y.nunique() < 2:
        return None, encoders, {"test_accuracy": None, "test_f1": None, "cv_f1": None}

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.20, random_state=config.random_state,
        stratify=y if y.value_counts().min() >= 2 else None
    )

    model = LGBMClassifier(
        random_state=config.random_state,
        verbose=-1,
        max_depth=config.order_max_depth,
        lambda_l2=1.0,
        n_estimators=config.n_estimators,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    pred = model.predict(X_test)
    metrics = {
        "test_accuracy": float(accuracy_score(y_test, pred)),
        "test_f1": float(f1_score(y_test, pred, zero_division=0)),
        "cv_f1": None,
    }

    class_counts = y.value_counts()
    folds = min(5, len(X), int(class_counts.min()))
    if folds >= 2:
        cv = StratifiedKFold(
            n_splits=folds, shuffle=True, random_state=config.random_state
        )
        scores = cross_val_score(model, X, y, cv=cv, scoring="f1")
        metrics["cv_f1"] = float(scores.mean())

    return model, encoders, metrics


def predict_customer_items(
    customer_data: pd.DataFrame,
    prediction_df: pd.DataFrame,
    hist: pd.DataFrame,
    first_order,
    order_freq,
    total_orders,
    encoders,
    config: ForecastConfig,
):
    if customer_data.empty or "item_name" not in customer_data.columns:
        prediction_df["predicted_items_quantities"] = None
        return prediction_df

    customer = customer_data.copy()
    customer["order_date"] = pd.to_datetime(customer["order_date"])

    customer["days_since_first_order"] = (
        customer["order_date"] - first_order
    ).dt.days
    customer["day_name"] = customer["order_date"].dt.day_name()

    day_encoder, dow, month, week = encoders
    customer["day_name_encoded"] = day_encoder.transform(customer["day_name"])
    customer["day_of_week"] = customer["order_date"].dt.weekday
    customer["month"] = customer["order_date"].dt.month
    customer["week_of_year"] = (
        customer["order_date"].dt.isocalendar().week.astype(int)
    )

    hist_order = hist[["date", "ordered_yesterday"]].copy()
    customer = customer.merge(
        hist_order,
        left_on="order_date",
        right_on="date",
        how="left",
    )
    customer["ordered_yesterday"] = customer["ordered_yesterday"].fillna(0)
    customer["order_frequency"] = order_freq
    customer["total_orders"] = total_orders

    # Match the feature order used by the source pipeline.
    X_product = pd.DataFrame({
        "day_name_encoded": customer["day_name_encoded"],
        "days_since_first_order": customer["days_since_first_order"],
        "ordered_yesterday": customer["ordered_yesterday"],
        "order_frequency": customer["order_frequency"],
        "total_orders": customer["total_orders"],
        "day_of_week_encoded": dow.transform(customer["day_of_week"].astype(int)),
        "month_encoded": month.transform(customer["month"].astype(int)),
        "week_of_year_encoded": week.transform(customer["week_of_year"].astype(int)),
    })

    item_model = RandomForestClassifier(
        random_state=config.random_state,
        n_estimators=config.n_estimators,
        max_depth=config.item_max_depth,
    )
    quantity_model = RandomForestRegressor(
        random_state=config.random_state,
        n_estimators=config.n_estimators,
        max_depth=config.quantity_max_depth,
    )

    item_model.fit(X_product, customer["item_name"])
    quantity_model.fit(X_product, customer["quantity"])

    max_orders_per_day = int(
        min(3, max(1, customer.groupby("order_date").size().max()))
    )

    results = []
    cumulative = set()

    for idx in prediction_df.index:
        if int(prediction_df.loc[idx, "predicted_order"]) != 1:
            results.append(None)
            continue

        row = prediction_df.loc[[idx], FEATURES]
        num_items = (
            np.random.default_rng(config.random_state + int(idx)).integers(
                1, max_orders_per_day + 1
            )
            if config.stochastic_item_count
            else 1
        )

        pairs = []
        for _ in range(int(num_items)):
            item = item_model.predict(row)[0]
            qty = max(1, int(round(quantity_model.predict(row)[0])))
            pairs.append((item, qty))
            cumulative.add(item)

        results.append(pairs)

    prediction_df["predicted_items_quantities"] = results
    prediction_df["cumulative_predicted_items"] = [
        list(cumulative) if x is not None else None for x in results
    ]
    return prediction_df


def forecast_orders(
    df: pd.DataFrame,
    start_date: str,
    end_date: str,
    config: Optional[ForecastConfig] = None,
):
    config = config or ForecastConfig()
    validate_orders(df)

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)
    if end < start:
        raise ValueError("end_date must be on or after start_date")

    date_range = pd.date_range(start, end, freq="D")
    encoders = build_encoders()
    day_encoder, dow, month, week = encoders

    all_predictions = []
    customer_metrics = []

    for customer_id in df["customer_id"].dropna().unique():
        customer = df[df["customer_id"] == customer_id].copy()
        customer, hist, first_order, freq, total = customer_history(customer, start)

        model, model_encoders, metrics = train_order_model(hist, config)
        # train_order_model creates equivalent fixed-range encoders; use our
        # global encoders for prediction so future dates are always encodable.
        if model is None:
            pred = pd.DataFrame({
                "customer_id": customer_id,
                "date": date_range,
                "day_name": date_range.day_name(),
                "probability_of_order": 0.0,
                "predicted_order": 0,
            })
        else:
            pred = pd.DataFrame({
                "customer_id": customer_id,
                "date": date_range,
                "day_name": date_range.day_name(),
            })
            pred["day_name_encoded"] = day_encoder.transform(pred["day_name"])
            pred["days_since_first_order"] = (
                pred["date"] - first_order
            ).dt.days
            pred["ordered_yesterday"] = 0
            pred["order_frequency"] = freq
            pred["total_orders"] = total
            pred["day_of_week"] = pred["date"].dt.weekday
            pred["month"] = pred["date"].dt.month
            pred["week_of_year"] = pred["date"].dt.isocalendar().week.astype(int)
            pred["day_of_week_encoded"] = dow.transform(pred["day_of_week"].astype(int))
            pred["month_encoded"] = month.transform(pred["month"].astype(int))
            pred["week_of_year_encoded"] = week.transform(pred["week_of_year"].astype(int))

            probabilities = model.predict_proba(pred[FEATURES])[:, 1]
            pred["probability_of_order"] = probabilities
            pred["predicted_order"] = (
                probabilities >= config.order_threshold
            ).astype(int)

            pred = predict_customer_items(
                customer, pred, hist, first_order, freq, total,
                encoders, config
            )

        customer_metrics.append({
            "customer_id": customer_id,
            **metrics,
        })
        all_predictions.append(pred)

    predictions = pd.concat(all_predictions, ignore_index=True)
    metrics = pd.DataFrame(customer_metrics)
    return predictions, metrics


def aggregate_warehouse_demand(
    predictions: pd.DataFrame,
    original_orders: pd.DataFrame,
):
    if "warehouse_id" not in original_orders.columns:
        raise ValueError(
            "warehouse_id is required for warehouse aggregation."
        )

    warehouse_map = (
        original_orders.groupby("customer_id")["warehouse_id"]
        .first()
        .reset_index()
    )
    df = predictions.merge(warehouse_map, on="customer_id", how="left")

    rows = []
    for _, row in df.iterrows():
        items = row.get("predicted_items_quantities")
        if isinstance(items, str):
            try:
                items = ast.literal_eval(items)
            except Exception:
                items = None
        if not isinstance(items, list):
            continue
        for item, qty in items:
            rows.append({
                "warehouse_id": row["warehouse_id"],
                "item_name": item,
                "predicted_quantity": qty,
            })

    if not rows:
        return pd.DataFrame(
            columns=["warehouse_id", "item_name", "predicted_quantity"]
        )

    return (
        pd.DataFrame(rows)
        .groupby(["warehouse_id", "item_name"], as_index=False)
        ["predicted_quantity"].sum()
    )
