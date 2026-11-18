-- No order may be dated after the fixed as_of_date var (deterministic —
-- never now(), so this test means the same thing on every run).
select order_id, order_date
from {{ ref('stg_orders') }}
where order_date > '{{ var("as_of_date") }}'::date
