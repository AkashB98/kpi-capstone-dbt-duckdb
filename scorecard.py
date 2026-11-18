#!/usr/bin/env python3
"""Render scorecard.md from the kpi_daily mart: last 30 days vs prior 30,
against the targets declared in models/marts/_kpi_daily.yml (mirrored here).

  python3 scorecard.py   # writes scorecard.md
"""
from pathlib import Path

import duckdb

ROOT = Path(__file__).parent
TARGETS = {  # mirror of the meta targets in models/marts/_kpi_daily.yml
    "revenue_dollars": (">=", 30000.0, "${:,.0f}"),
    "orders": (">=", 330, "{:,.0f}"),
    "aov_dollars": (">=", 88.0, "${:,.2f}"),
    "conversion_rate": (">=", 0.030, "{:.3%}"),
    "refund_rate": ("<=", 0.022, "{:.2%}"),
}


def main() -> None:
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    agg = """select sum(revenue_dollars)/count(*), sum(orders)*1.0/count(*),
                    sum(revenue_dollars)/sum(orders), sum(orders)*1.0/sum(visitors),
                    avg(refund_rate)
             from analytics.kpi_daily where kpi_date between ? and ?"""
    cur = con.execute(agg, ["2026-03-02", "2026-03-31"]).fetchone()
    pri = con.execute(agg, ["2026-01-31", "2026-03-01"]).fetchone()
    con.close()
    names = ["Revenue / day", "Orders / day", "AOV", "Conversion rate", "Refund rate"]
    keys = list(TARGETS)
    lines = ["# Helios Home — KPI scorecard (from the dbt mart `kpi_daily`)", "",
             "| Metric | Current (Mar 2–31) | Prior (Jan 31–Mar 1) | Δ | Target | Status |",
             "|---|---|---|---|---|---|"]
    for name, key, c, p in zip(names, keys, cur, pri):
        op, target, fmt = TARGETS[key]
        ok = c >= target if op == ">=" else c <= target
        delta = (c - p) / p if p else 0.0
        lines.append(f"| {name} | {fmt.format(c)} | {fmt.format(p)} | {delta:+.1%} | "
                     f"{op} {fmt.format(target)} | {'🟢' if ok else '🔴'} |")
    (ROOT / "scorecard.md").write_text("\n".join(lines) + "\n")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
