#!/usr/bin/env python3
"""End-to-end verification for the dbt capstone. Proves, in order:

1. INCREMENTAL == FULL REFRESH: build Jan-Feb incrementally, load March,
   build again — the mart checksum must equal a from-scratch full build.
2. SNAPSHOT (SCD2): after the Chicago region update, stores_snapshot must
   hold exactly 2 versions of S4 and dim_stores must show Central.
3. DOCS + FRESHNESS: `dbt docs generate` and `dbt source freshness` pass.
4. PLANTED FAILURE: on the `bad` target (one duplicate order_id planted),
   `dbt build` must FAIL on a unique test. A test never seen failing
   proves nothing.

Exit 0 only if every phase behaves as expected. Run inside the venv:
  DBT_PROFILES_DIR=. .venv/bin/python check.py
"""
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parent
ENV = dict(os.environ, DBT_PROFILES_DIR=".")
FAILURES = []


def run(cmd, expect_zero=True, capture=False):
    print(f"\n$ {' '.join(cmd)}")
    r = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=capture, text=True)
    out = (r.stdout or "") + (r.stderr or "") if capture else ""
    if capture:
        print(out[-1500:])
    ok = (r.returncode == 0) == expect_zero
    if not ok:
        FAILURES.append(f"{' '.join(cmd)} -> exit {r.returncode} (expected {'0' if expect_zero else 'non-zero'})")
    return r, out


def mart_checksum(db="warehouse.duckdb"):
    import duckdb
    con = duckdb.connect(str(ROOT / db), read_only=True)
    row = con.execute(
        "select count(*), sum(orders), sum(revenue_cents) from analytics.kpi_daily"
    ).fetchone()
    con.close()
    return row


def main() -> int:
    dbt = [sys.executable.replace("python", "dbt")] if (ROOT / ".venv").exists() else ["dbt"]
    # Prefer a dbt sitting next to this interpreter (venv), else PATH.
    import shutil
    dbt_bin = shutil.which("dbt", path=str(Path(sys.executable).parent)) or "dbt"
    dbt = [dbt_bin]
    py = [sys.executable]

    run(py + ["generate_sources.py"])

    # ---- Phase 1: incremental == full refresh ------------------------------
    (ROOT / "warehouse.duckdb").unlink(missing_ok=True)
    run(py + ["load_raw.py", "--through", "2026-02-28"])
    run(dbt + ["build", "--full-refresh"])
    run(py + ["load_raw.py"])  # full raw data now in sources
    run(dbt + ["build"])        # <- this run is incremental for stg_orders
    incremental_checksum = mart_checksum()
    print("incremental-path mart checksum:", incremental_checksum)

    (ROOT / "warehouse.duckdb").unlink(missing_ok=True)
    run(py + ["load_raw.py"])
    run(dbt + ["build", "--full-refresh"])
    full_checksum = mart_checksum()
    print("full-refresh mart checksum:  ", full_checksum)
    if incremental_checksum != full_checksum:
        FAILURES.append(f"incremental checksum {incremental_checksum} != full-refresh {full_checksum}")

    # ---- Phase 2: snapshot SCD2 --------------------------------------------
    run(py + ["load_raw.py", "--apply-store-update"])
    run(dbt + ["snapshot"])
    run(dbt + ["build"])
    import duckdb
    con = duckdb.connect(str(ROOT / "warehouse.duckdb"), read_only=True)
    versions = con.execute(
        "select count(*) from analytics_snapshots.stores_snapshot where store_id = 'S4'"
    ).fetchone()[0]
    current = con.execute(
        "select region from analytics.dim_stores where store_id = 'S4'"
    ).fetchone()[0]
    con.close()
    print(f"S4 snapshot versions: {versions}, current region: {current}")
    if versions != 2:
        FAILURES.append(f"expected 2 snapshot versions of S4, got {versions}")
    if current != "Central":
        FAILURES.append(f"dim_stores S4 region should be Central, got {current}")

    # ---- Phase 3: docs + freshness ------------------------------------------
    run(dbt + ["docs", "generate"])
    run(dbt + ["source", "freshness"])

    # ---- Phase 4: planted failure must fail ---------------------------------
    (ROOT / "warehouse_bad.duckdb").unlink(missing_ok=True)
    run(py + ["load_raw.py", "--bad", "--db", "warehouse_bad.duckdb"])
    r, out = run(dbt + ["build", "--target", "bad"], expect_zero=False, capture=True)
    if "unique" not in out.lower():
        FAILURES.append("bad-target build failed, but not on a unique test (see output above)")

    print("\n" + "=" * 60)
    if FAILURES:
        print("CHECK FAILED:")
        for f in FAILURES:
            print(" -", f)
        return 1
    print("CHECK PASSED: incremental == full-refresh, SCD2 snapshot holds history,")
    print("docs + freshness green, and the planted duplicate fails the build on a unique test.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
