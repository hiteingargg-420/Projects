# Customer Order & SKU Demand Forecasting

Predicts, per customer, whether they'll place an order on a given day,
which items they're likely to order, and in what quantity -- then
aggregates those predictions into warehouse-level SKU demand for
procurement and fulfillment planning.

## Pipeline

```
Order history (customer_id, order_date, item_name, quantity, warehouse_id)
  -> customer-level feature engineering (order frequency, recency, day-of-week/month patterns)
  -> per-customer order-day probability      (LightGBM classifier)
  -> per-customer item prediction             (Random Forest classifier)
  -> per-customer quantity prediction          (Random Forest regressor)
  -> warehouse/SKU aggregation
  -> Excel outputs
```

## Quick start

```bash
pip install -r requirements.txt

# Build an order-level dataset from the warehouse/SKU source data
python scripts/generate_anchored_dataset.py --customers-per-warehouse 20

# Run the forecast
python scripts/run_forecasting.py --input data/orders.csv --start 2026-01-01 --end 2026-01-14
```

The pipeline trains a separate model per customer (see "Notes on runtime"
below), so `--customers-per-warehouse` trades off runtime against customer
coverage. 20 per warehouse (120 customers total) completes in a little
over 2 minutes and is what the results below were measured on; raising it
to 100 per warehouse (600 customers) is architecturally the same run, just
slower (~8-9 minutes).

Outputs are written to `outputs/`:
- `customer_order_item_predictions.xlsx` -- per-customer predicted orders, items, quantities
- `order_model_metrics.csv` -- per-customer accuracy/F1 for the order-day model
- `warehouse_sku_demand.xlsx` -- predicted demand aggregated by warehouse and SKU

## Data

`data/source/` holds two real, aggregated files: a 6-warehouse x 261-item
quantity matrix (`final_quantity_per_inventory.xlsx`) and a matching
item-price table (`label_encoded_with_prices.xlsx`) giving the real item
catalog, real prices, real warehouse structure, and the real total
quantity moved per (warehouse, item).

No raw order-level export (one row per individual transaction) is
available, so `scripts/generate_anchored_dataset.py` builds one by
disaggregating each real (warehouse, item) total into individual
synthetic order lines, distributed across a configurable number of
simulated customers and order dates. The disaggregation is constrained,
not free-floating: summing the generated data back up by (warehouse,
item) reproduces the real totals exactly, which is checked automatically
and written to `data/anchor_reconciliation.csv` (0 mismatches, verified
against 1,050 warehouse/item pairs covering 548,641 real units, regardless
of how many customers those units get distributed across).

**What's real:** the item catalog, item prices, warehouse structure, and
historical total quantity moved per warehouse/item.
**What's simulated:** individual customer identities, order dates, and
how a (warehouse, item) total splits into individual order lines.

## Results

Measured on the 120-customer run shipped in `outputs/` (20 per warehouse):
- Mean per-customer order-day prediction accuracy: **71.2%**
- Mean per-customer F1: **0.174**
- Mean per-customer cross-validated F1: **0.165**

At 300 customers (50 per warehouse), a separate full run measured
accuracy 72.1% / F1 0.160 -- consistent with the 120-customer numbers
above, suggesting these figures are stable rather than an artifact of
customer count.

The F1 score is reported alongside accuracy deliberately: order days are
a minority class for most customers (roughly 5-20% of days), so accuracy
alone overstates how well the model identifies *when* a customer will
actually order -- a model that mostly predicts "no order" can still score
well on accuracy. F1 is the more honest single number for how good the
order-day predictions actually are.

## Notes on runtime

The pipeline trains a separate model per customer rather than one shared
model, so total runtime scales with customer count. Measured directly:
120 customers completed in ~2.3 minutes; 300 customers in ~4.3 minutes.
Runtime scales roughly linearly with customer count in this environment,
so 600 customers should take somewhere in the 8-9 minute range, though
that exact figure hasn't been directly measured here. This is a design
tradeoff (per-customer models can capture individual ordering patterns
that a single global model would average away) rather than a bug.
