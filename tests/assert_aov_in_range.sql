-- Daily AOV must sit in a sane band for this store ($40–$200).
select kpi_date, aov_dollars
from {{ ref('kpi_daily') }}
where aov_dollars < 40 or aov_dollars > 200
