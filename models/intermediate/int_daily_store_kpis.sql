-- One row per store per day: order KPIs joined to traffic at the same grain.
with orders as (
    select
        order_date,
        store_id,
        count(*) as orders,
        sum(net_cents) as revenue_cents,
        sum(refund_cents) as refund_cents,
        sum(gross_cents - discount_cents) as sold_cents
    from {{ ref('stg_orders') }}
    group by 1, 2
),
traffic as (
    select traffic_date, store_id, visitors, sessions
    from {{ ref('stg_daily_traffic') }}
)
select
    o.order_date as kpi_date,
    o.store_id,
    o.orders,
    o.revenue_cents,
    o.refund_cents,
    o.sold_cents,
    t.visitors,
    t.sessions,
    case when o.orders > 0 then o.revenue_cents * 1.0 / o.orders end as aov_cents,
    case when t.visitors > 0 then o.orders * 1.0 / t.visitors end as conversion_rate,
    case when o.sold_cents > 0 then o.refund_cents * 1.0 / o.sold_cents end as refund_rate
from orders o
join traffic t
    on t.traffic_date = o.order_date
    and t.store_id = o.store_id
