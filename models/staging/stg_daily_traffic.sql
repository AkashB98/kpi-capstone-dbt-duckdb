select
    traffic_date::date as traffic_date,
    store_id,
    visitors::bigint as visitors,
    sessions::bigint as sessions
from {{ source('raw', 'daily_traffic') }}
