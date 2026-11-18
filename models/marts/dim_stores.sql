-- Current store dimension, read from the SCD2 snapshot so a region
-- change never rewrites history: this mart shows the CURRENT row only;
-- the snapshot table itself keeps every version.
select
    s.store_id,
    s.city,
    s.region,
    r.opened_on,
    r.store_format,
    s.dbt_valid_from as region_valid_from
from {{ ref('stores_snapshot') }} s
join {{ ref('stores_reference') }} r on r.store_id = s.store_id
where s.dbt_valid_to is null
