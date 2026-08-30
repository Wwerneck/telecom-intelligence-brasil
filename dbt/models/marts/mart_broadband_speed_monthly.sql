with aggregated as (
    select
        date_key,
        reference_year,
        reference_month,
        speed_range,
        sum(accesses) as accesses,
        count(distinct municipality_id) as municipalities
    from {{ ref('stg_fact_broadband_accesses') }}
    group by 1, 2, 3, 4
)
select
    md5(concat_ws('|', date_key::text, speed_range)) as speed_month_id,
    *,
    accesses::numeric / nullif(sum(accesses) over (partition by date_key), 0) * 100
        as speed_range_share_pct
from aggregated
