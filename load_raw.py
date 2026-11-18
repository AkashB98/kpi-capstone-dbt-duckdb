#!/usr/bin/env python3
"""Load data/raw/*.csv into the DuckDB warehouse as the `raw` schema.

These tables are declared as dbt SOURCES (models/sources.yml) — generated
data lands as sources; dbt seeds are reserved for small reference tables.

Usage:
  python3 load_raw.py                      # clean load into warehouse.duckdb
  python3 load_raw.py --through 2026-02-28 # only rows up to a date (incremental demo)
  python3 load_raw.py --apply-store-update # Chicago region Midwest -> Central, updated_at 2026-02-15
  python3 load_raw.py --bad --db warehouse_bad.duckdb  # planted duplicate order (test-failure demo)
"""
import argparse
from datetime import datetime, timezone
from pathlib import Path

import duckdb

ROOT = Path(__file__).parent
RAW = ROOT / "data" / "raw"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", default=str(ROOT / "warehouse.duckdb"))
    ap.add_argument("--through", default=None, help="only load orders/traffic dated <= this date")
    ap.add_argument("--apply-store-update", action="store_true")
    ap.add_argument("--bad", action="store_true", help="plant one duplicate order_id")
    args = ap.parse_args()

    loaded_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    con = duckdb.connect(args.db)
    con.execute("create schema if not exists raw")

    thru_o = f" where order_date <= '{args.through}'" if args.through else ""
    thru_t = f" where traffic_date <= '{args.through}'" if args.through else ""
    con.execute(f"""create or replace table raw.orders as
        select *, '{loaded_at}'::timestamp as loaded_at
        from read_csv('{RAW / 'orders.csv'}', header=true){thru_o}""")
    con.execute(f"""create or replace table raw.daily_traffic as
        select *, '{loaded_at}'::timestamp as loaded_at
        from read_csv('{RAW / 'daily_traffic.csv'}', header=true){thru_t}""")
    con.execute(f"""create or replace table raw.stores as
        select *, '{loaded_at}'::timestamp as loaded_at
        from read_csv('{RAW / 'stores.csv'}', header=true)""")

    if args.apply_store_update:
        con.execute("""update raw.stores
            set region = 'Central', updated_at = '2026-02-15 00:00:00'::timestamp
            where store_id = 'S4'""")
        print("store update applied: S4 region Midwest -> Central (updated_at 2026-02-15)")

    if args.bad:
        con.execute("""insert into raw.orders
            select * from raw.orders where order_id = 'ORD-000001' limit 1""")
        print("BAD fixture planted: duplicate order_id ORD-000001")

    for t in ("orders", "daily_traffic", "stores"):
        n = con.execute(f"select count(*) from raw.{t}").fetchone()[0]
        print(f"raw.{t}: {n} rows (loaded_at {loaded_at})")
    con.close()


if __name__ == "__main__":
    main()
