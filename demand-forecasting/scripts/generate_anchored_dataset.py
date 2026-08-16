"""
Build an order-level dataset (customer_id, order_date, item_name, quantity,
warehouse_id) that is ANCHORED to real project data:

  - real 261-item grocery catalog       (from label_encoded_with_prices.xlsx)
  - real per-item prices                (from label_encoded_with_prices.xlsx)
  - real 6 warehouses                   (inv_1..inv_6, from final_quantity_per_inventory.xlsx)
  - real total quantity moved per (warehouse, item) over the historical period
    (from final_quantity_per_inventory.xlsx)

What is NOT real and IS fabricated, because no raw order-level export
(individual order lines, one per transaction) currently exists -- only the
aggregated warehouse/SKU totals below were available:
  - individual customer_ids
  - individual order dates
  - which specific order an item line belongs to
  - the split of a warehouse/item total into individual order-line quantities

The fabricated part is constrained (not free-floating): every order-line
quantity is drawn so that, once regenerated data is summed back up per
(warehouse, item), it reproduces the real historical total exactly. That
means the forecasting model is trained on synthetic transactions, but the
ground truth it's trying to reproduce is real.

Output: data/orders.csv (schema matches src/forecasting/pipeline.py)
        data/anchor_reconciliation.csv (proof the disaggregation sums back
        up correctly, per warehouse/item)
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

SOURCE_DIR = Path("data/source")
OUT_DIR = Path("data")

WAREHOUSE_LABEL_ENCODED_ROW = "inv_7"  # leftover encoding artifact, not a real warehouse


def load_real_totals():
    qty = pd.read_excel(SOURCE_DIR / "final_quantity_per_inventory.xlsx")
    qty = qty[qty["inventory_row"] != WAREHOUSE_LABEL_ENCODED_ROW]
    qty = qty.drop(columns=["Unnamed: 0"]).set_index("inventory_row")

    priced = pd.read_excel(SOURCE_DIR / "label_encoded_with_prices.xlsx")
    price_row = priced[priced["Unnamed: 0"] == "item_price"].drop(columns=["Unnamed: 0"]).iloc[0]

    common_items = [c for c in qty.columns if c in price_row.index]
    qty = qty[common_items]
    prices = price_row[common_items].astype(float)

    return qty, prices


def build_customer_order_calendars(rng, warehouses, customers_per_warehouse, start, end):
    """Each customer gets a random subset of days on which they place *an*
    order (item-agnostic). Item lines are attached to these days later, same
    pattern the rest of the pipeline already assumes (order-day probability
    per customer)."""
    dates = pd.date_range(start, end, freq="D")
    calendars = {}
    customer_warehouse = {}
    customer_id = 1

    for w in warehouses:
        for _ in range(customers_per_warehouse):
            p = float(rng.uniform(0.05, 0.20))
            order_days = dates[rng.random(len(dates)) < p]
            if len(order_days) == 0:
                order_days = dates[rng.integers(0, len(dates), size=1)]
            calendars[customer_id] = list(order_days)
            customer_warehouse[customer_id] = w
            customer_id += 1

    return calendars, customer_warehouse


def split_quantity(rng, total_qty, num_lines, min_line_qty=1):
    """Split an integer total into num_lines positive integers that sum
    exactly to total_qty."""
    if num_lines <= 1:
        return [int(total_qty)]
    raw = rng.dirichlet(np.ones(num_lines)) * total_qty
    lines = np.floor(raw).astype(int)
    lines = np.maximum(lines, min_line_qty - 1)  # allow 0 pre-fix
    remainder = int(total_qty - lines.sum())

    # Hand out the remainder (could be negative if flooring+min pushed over)
    idx_order = np.argsort(-raw)  # give remainder to biggest shares first
    i = 0
    while remainder > 0:
        lines[idx_order[i % num_lines]] += 1
        remainder -= 1
        i += 1
    while remainder < 0:
        j = idx_order[i % num_lines]
        if lines[j] > min_line_qty:
            lines[j] -= 1
            remainder += 1
        i += 1

    lines = np.maximum(lines, min_line_qty)
    diff = int(total_qty - lines.sum())
    if diff != 0:
        lines[idx_order[0]] += diff  # final exact-sum guarantee

    return lines.tolist()


def generate(customers_per_warehouse: int, start: str, end: str, seed: int = 42):
    rng = np.random.default_rng(seed)
    qty_matrix, prices = load_real_totals()
    warehouses = qty_matrix.index.tolist()

    calendars, customer_warehouse = build_customer_order_calendars(
        rng, warehouses, customers_per_warehouse, start, end
    )
    warehouse_customers = {
        w: [c for c, wh in customer_warehouse.items() if wh == w] for w in warehouses
    }

    rows = []
    reconciliation = []

    for w in warehouses:
        w_customers = warehouse_customers[w]
        for item in qty_matrix.columns:
            total_qty = int(qty_matrix.loc[w, item])
            if total_qty <= 0:
                continue

            avg_line_qty = rng.uniform(3, 12)
            num_lines = max(1, min(total_qty, round(total_qty / avg_line_qty)))
            line_quantities = split_quantity(rng, total_qty, num_lines)

            for q in line_quantities:
                customer = w_customers[rng.integers(0, len(w_customers))]
                order_days = calendars[customer]
                order_date = order_days[rng.integers(0, len(order_days))]
                rows.append({
                    "customer_id": customer,
                    "order_date": order_date,
                    "item_name": item,
                    "quantity": int(q),
                    "warehouse_id": w,
                    "item_price": float(prices[item]),
                })

            reconciliation.append({
                "warehouse_id": w,
                "item_name": item,
                "real_total_quantity": total_qty,
                "generated_total_quantity": int(sum(line_quantities)),
                "num_order_lines": num_lines,
            })

    orders = pd.DataFrame(rows).sort_values(["order_date", "customer_id"]).reset_index(drop=True)
    recon = pd.DataFrame(reconciliation)

    OUT_DIR.mkdir(exist_ok=True)
    orders.to_csv(OUT_DIR / "orders.csv", index=False)
    recon.to_csv(OUT_DIR / "anchor_reconciliation.csv", index=False)

    mismatches = (recon["real_total_quantity"] != recon["generated_total_quantity"]).sum()
    print(f"Customers: {len(calendars)} ({customers_per_warehouse} x {len(warehouses)} warehouses)")
    print(f"Order lines: {len(orders)}")
    print(f"Warehouse/item pairs reconciled: {len(recon)}")
    print(f"Mismatched totals: {mismatches} (should be 0)")
    print(f"Real total units anchored: {int(qty_matrix.values.sum())}")
    print(f"Generated total units:     {int(orders['quantity'].sum())}")


def main():
    parser = argparse.ArgumentParser(
        description="Generate an order-level dataset anchored to real warehouse/SKU totals"
    )
    parser.add_argument("--customers-per-warehouse", type=int, default=50)
    parser.add_argument("--start", default="2025-01-01")
    parser.add_argument("--end", default="2025-06-30")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    generate(args.customers_per_warehouse, args.start, args.end, args.seed)


if __name__ == "__main__":
    main()
