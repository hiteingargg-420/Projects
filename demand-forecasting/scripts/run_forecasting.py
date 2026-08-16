import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd

from src.forecasting.pipeline import (
    ForecastConfig, forecast_orders, aggregate_warehouse_demand
)

def main():
    parser = argparse.ArgumentParser(description="Customer order/SKU forecasting")
    parser.add_argument("--input", required=True)
    parser.add_argument("--start", required=True, help="YYYY-MM-DD")
    parser.add_argument("--end", required=True, help="YYYY-MM-DD")
    parser.add_argument("--threshold", type=float, default=0.20)
    args = parser.parse_args()

    df = pd.read_csv(args.input)
    cfg = ForecastConfig(order_threshold=args.threshold)

    predictions, metrics = forecast_orders(df, args.start, args.end, cfg)

    out = Path("outputs")
    out.mkdir(exist_ok=True)

    predictions.to_excel(out / "customer_order_item_predictions.xlsx", index=False)
    metrics.to_csv(out / "order_model_metrics.csv", index=False)

    if "warehouse_id" in df.columns:
        warehouse = aggregate_warehouse_demand(predictions, df)
        warehouse.to_excel(out / "warehouse_sku_demand.xlsx", index=False)

    print("Forecasting complete.")
    print(f"Predictions: {out / 'customer_order_item_predictions.xlsx'}")
    print(f"Metrics:     {out / 'order_model_metrics.csv'}")

if __name__ == "__main__":
    main()
