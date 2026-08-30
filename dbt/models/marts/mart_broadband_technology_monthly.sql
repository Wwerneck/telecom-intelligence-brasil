with aggregated as (
    select
        date_key,
        reference_year,
        reference_month,
        technology,
        access_medium,
        sum(accesses) as accesses,
        count(distinct municipality_id) as municipalities
    from {{ ref('stg_fact_broadband_accesses') }}
    group by 1, 2, 3, 4, 5
)
select
    md5(concat_ws('|', date_key::text, technology, access_medium)) as technology_month_id,
    *,
    accesses::numeric / nullif(sum(accesses) over (partition by date_key), 0) * 100
        as technology_share_pct
from aggregated
