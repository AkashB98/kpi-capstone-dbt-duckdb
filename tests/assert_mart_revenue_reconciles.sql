-- The mart must reconcile to staging to the cent. Returns rows = failure.
select
    (select sum(net_cents) from {{ ref('stg_orders') }}) as staging_cents,
    (select sum(revenue_cents) from {{ ref('kpi_daily') }}) as mart_cents
where (select sum(net_cents) from {{ ref('stg_orders') }})
   <> (select sum(revenue_cents) from {{ ref('kpi_daily') }})
