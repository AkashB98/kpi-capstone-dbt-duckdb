#!/usr/bin/env python3
"""Generate the synthetic raw data for the KPI capstone (seed 42).

Writes CSVs under data/raw/ that load_raw.py loads as dbt SOURCES.
Fictional company: Helios Home (smart-home store), same fictional
company as the exec-kpi-kit portfolio repo — this project is the
warehouse modelling layer underneath those KPIs.

Deterministic: same seed -> same CSVs, byte for byte.
"""
import csv
import random
from datetime import date, timedelta
from pathlib import Path

SEED = 42
START = date(2026, 1, 1)
DAYS = 90
OUT = Path(__file__).parent / "data" / "raw"

STORES = [
    ("S1", "Austin", "South"),
    ("S2", "Dallas", "South"),
    ("S3", "Seattle", "West"),
    ("S4", "Chicago", "Midwest"),  # region changes to Central on 2026-02-15 (see load_raw.py --apply-store-update)
]
CHANNELS = ["web", "mobile_app", "in_store"]


def main() -> None:
    rng = random.Random(SEED)
    OUT.mkdir(parents=True, exist_ok=True)

    # --- orders -------------------------------------------------------------
    orders = []
    oid = 0
    for d in range(DAYS):
        day = START + timedelta(days=d)
        growth = 1.0 + 0.003 * d
        weekend = 1.25 if day.weekday() >= 5 else 1.0
        for store_id, _city, _region in STORES:
            n = int(rng.gauss(92, 14) * growth * weekend)
            for _ in range(max(n, 1)):
                oid += 1
                channel = rng.choices(CHANNELS, weights=[0.5, 0.3, 0.2])[0]
                gross = int(rng.gauss(9800, 3600))
                gross = max(gross, 1200)
                discount = int(gross * rng.choice([0, 0, 0, 0.05, 0.10, 0.15]))
                refund = 0
                r = rng.random()
                if r < 0.02:
                    refund = gross - discount  # full refund
                elif r < 0.035:
                    refund = int((gross - discount) * 0.5)  # partial refund
                status = "completed" if refund == 0 else ("refunded" if refund == gross - discount else "partially_refunded")
                orders.append({
                    "order_id": f"ORD-{oid:06d}",
                    "order_date": day.isoformat(),
                    "store_id": store_id,
                    "channel": channel,
                    "status": status,
                    "customer_id": f"CUST-{rng.randint(1, 9000):05d}",
                    "gross_cents": gross,
                    "discount_cents": discount,
                    "refund_cents": refund,
                })
    with open(OUT / "orders.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(orders[0].keys()))
        w.writeheader()
        w.writerows(orders)

    # --- daily traffic ------------------------------------------------------
    traffic = []
    for d in range(DAYS):
        day = START + timedelta(days=d)
        growth = 1.0 + 0.003 * d
        weekend = 1.25 if day.weekday() >= 5 else 1.0
        for store_id, _city, _region in STORES:
            visitors = int(rng.gauss(2950, 320) * growth * weekend)
            traffic.append({
                "traffic_date": day.isoformat(),
                "store_id": store_id,
                "visitors": max(visitors, 100),
                "sessions": int(visitors * rng.uniform(1.15, 1.35)),
            })
    with open(OUT / "daily_traffic.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(traffic[0].keys()))
        w.writeheader()
        w.writerows(traffic)

    # --- stores (v1: as of 2026-01-01; Chicago still Midwest) ---------------
    with open(OUT / "stores.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["store_id", "city", "region", "updated_at"])
        for store_id, city, region in STORES:
            w.writerow([store_id, city, region, "2026-01-01 00:00:00"])

    print(f"orders: {len(orders)} rows -> {OUT / 'orders.csv'}")
    print(f"daily_traffic: {len(traffic)} rows -> {OUT / 'daily_traffic.csv'}")
    print(f"stores: {len(STORES)} rows -> {OUT / 'stores.csv'}")


if __name__ == "__main__":
    main()
