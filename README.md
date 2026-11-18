# kpi-capstone-dbt-duckdb

**A real dbt project: the KPI warehouse for a fictional store, modelled in dbt on DuckDB — sources with freshness checks, an incremental staging model, an SCD2 snapshot, tested marts, and metric definitions in YAML.**

Every analytics-engineering job description asks for the same thing: can you own the models — not just write SQL against someone else's? This project is that ownership, end to end, in the tool those jobs name: **dbt** — a tool that turns SQL files into a tested, documented data pipeline. It rebuilds the KPI story from [exec-kpi-kit](https://github.com/AkashB98/exec-kpi-kit) as a proper warehouse layer: exec-kpi-kit computes KPIs in Python; this repo is the **modelling layer underneath** — raw data lands as sources, staging cleans it once, and every KPI in the mart traces back to one definition.

> **Synthetic data only.** Every figure is fabricated by a seeded generator for a fictional smart-home store (**Helios Home**). No real company, customer, or revenue data is used anywhere in this project.

> **First non-stdlib repo in this portfolio — on purpose.** Every other project here is dependency-free Python. This one breaks that convention because the skill being demonstrated *is* the toolchain: dbt-core 1.12.7, dbt-duckdb 1.11.1, DuckDB 2.0.0, Python 3.12 (all pinned in `requirements.txt`).

## Quickstart

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
export DBT_PROFILES_DIR=.          # profiles.yml is committed; no home-dir setup

.venv/bin/python generate_sources.py   # synthetic raw CSVs (seed 42)
.venv/bin/python load_raw.py           # load them as the `raw` source tables
.venv/bin/dbt snapshot                 # capture store dimension v1
.venv/bin/python load_raw.py --apply-store-update   # Chicago changes region
.venv/bin/dbt build                    # seeds + snapshot + models + 21 tests
.venv/bin/python scorecard.py          # KPI scorecard from the mart
.venv/bin/python check.py              # full verification (see below)
```

## What the build proves (verified numbers, seed 42)

- `dbt build`: **29/29 PASS** — 2 seeds, 1 snapshot, 5 models (1 **incremental** — only new rows are processed on repeat runs; 1 view, 3 tables), 20 data tests + 1 **unit test** — a test of one model's math on hand-computed rows, before any real data touches it.
- Data: **40,213 orders** over 90 days (2026-01-01 → 2026-03-31), **$3,649,742.50** net revenue in the mart, reconciled to staging **to the cent** by a singular SQL test.
- **Incremental == full refresh:** `check.py` builds Jan–Feb, loads March, builds again incrementally, and asserts the mart checksum `(90 days, 40213 orders, 364974250 cents)` is identical to a from-scratch full build. It is.
- **Snapshot (SCD2** — slowly changing dimension, type 2: keep every historical version of a row instead of overwriting it**)**: Chicago's region changes Midwest → Central on 2026-02-15; `stores_snapshot` holds exactly **2 versions** of that store and `dim_stores` shows the current one (Central).
- **Planted failure:** a separate `bad` target loads one duplicate `order_id`; `dbt build` **fails on the unique test**, and `check.py` asserts that it does. A test that has never been seen to fail proves nothing.
- **Freshness:** sources declare `loaded_at_field` with warn/error windows; `dbt source freshness` passes right after a load (it is part of `check.py`).

Scorecard from the mart (last 30 days vs prior 30): revenue/day **$43,943** (+8.1%), orders/day **485**, AOV **$90.60**, conversion **3.091%** — and refund rate **3.00% 🔴** against a ≤2.20% target. The red is real: the generator plants refund incidence the target wasn't set for, and the scorecard says so instead of quietly passing.

## How it works

```
generate_sources.py -> data/raw/*.csv -> load_raw.py -> raw.* (dbt SOURCES, freshness-checked)
seeds/ (stores_reference, channel_map — small reference tables only, per dbt convention)
models/staging/      stg_orders (INCREMENTAL, net_cents computed once), stg_daily_traffic
models/intermediate/ int_daily_store_kpis (store-day grain; unit-tested math)
models/marts/        kpi_daily (company-day KPIs), dim_stores (current row from the snapshot)
snapshots/           stores_snapshot (SCD2 on raw.stores, timestamp strategy)
tests/               singular SQL tests: mart↔staging reconciliation, no future-dated
                     orders (against the fixed var as_of_date — never now(), so the
                     test means the same thing on every run), AOV sanity band
```

**Metric definitions** live in `models/marts/_kpi_daily.yml`, one `meta` block per column (formula + target). Honest naming: these are metric definitions in YAML. This project does **not** run dbt's MetricFlow semantic layer, and no README wording claims it does.

Money is integer cents end to end (`net_cents = gross − discount − refund`); dollars appear only at the mart's display columns.

## Honest limits

- **Local DuckDB, not Snowflake or BigQuery.** The adapter is DuckDB; the SQL and project structure are warehouse-shaped, but nothing here proves cloud-warehouse operations (grants, clustering, cost management).
- **No orchestration.** No Airflow, no scheduler — `check.py` and the GitHub Actions workflow (`.github/workflows/dbt.yml`, runs `dbt build` on push) are the only runners.
- **Small synthetic data.** ~40k orders is a correctness demo, not a scale demo; the incremental model exists to prove the pattern, not because the data needs it.
- The incremental filter is on `order_date`; a late-arriving order dated in an already-built period would need a full refresh — stated here because a real deployment would choose a lookback window instead.

## Client handoff — what changes on a real warehouse

This is the section a forward deployed / analytics engineer writes when handing the project to a client team:

1. **Profile:** swap `profiles.yml` to the client's warehouse (Snowflake/BigQuery adapter + role/warehouse); no model SQL changes except dialect-specific functions (this project uses none beyond standard SQL and one `::date` cast).
2. **Sources:** point `models/sources.yml` at the client's raw schema; keep the freshness windows — they are the contract that upstream data arrived.
3. **Incremental strategy:** on a warehouse with real volume, switch `stg_orders` to the warehouse's merge strategy and add a 3-day lookback for late-arriving orders.
4. **Grants & environments:** add a `prod` target with least-privilege roles (read raw, write analytics), and promote via the same `dbt build` gate in CI.
5. **What stays identical:** the tests. Reconciliation, uniqueness, accepted values, and the unit test are the handoff — they are how the client knows the numbers survived the move.

## POC framing

Framed as a proof of concept for a client whose KPI deck is hand-built from three dashboards: **success criteria declared up front** — (1) mart reconciles to source to the cent, (2) incremental and full builds agree exactly, (3) a planted data defect fails the build loudly, (4) one person's region change is preserved as history, not overwritten. All four are checked by `check.py` on every run; a POC that can't state its pass/fail before it starts isn't a POC, it's a demo.
