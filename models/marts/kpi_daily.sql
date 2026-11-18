-- Company-level daily KPI mart: one row per day, all stores combined.
-- Metric definitions live in models/marts/_kpi_daily.yml (meta block).
select
    kpi_date,
    sum(orders) as orders,
    sum(revenue_cents) as revenue_cents,
    sum(revenue_cents) / 100.0 as revenue_dollars,
    sum(visitors) as visitors,
    sum(revenue_cents) * 1.0 / nullif(sum(orders), 0) / 100.0 as aov_dollars,
    sum(orders) * 1.0 / nullif(sum(visitors), 0) as conversion_rate,
    sum(refund_cents) * 1.0 / nullif(sum(sold_cents), 0) as refund_rate
from {{ ref('int_daily_store_kpis') }}
group by 1
