{{ config(materialized="incremental", unique_key="order_id", on_schema_change="fail") }}

-- Typed, cleaned orders. Net revenue is computed ONCE here:
-- net_cents = gross_cents - discount_cents - refund_cents (integer cents, never floats).
select
    order_id,
    order_date::date as order_date,
    store_id,
    channel,
    status,
    customer_id,
    gross_cents::bigint as gross_cents,
    discount_cents::bigint as discount_cents,
    refund_cents::bigint as refund_cents,
    (gross_cents - discount_cents - refund_cents)::bigint as net_cents
from {{ source('raw', 'orders') }}

{% if is_incremental() %}
where order_date::date > (select max(order_date) from {{ this }})
{% endif %}
