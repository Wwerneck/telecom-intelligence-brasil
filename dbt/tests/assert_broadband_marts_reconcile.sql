with fact as (
    select date_key, sum(accesses) as accesses
    from {{ ref('stg_fact_broadband_accesses') }}
    group by 1
),
national as (
    select date_key, accesses
    from {{ ref('mart_broadband_national_monthly') }}
)
select coalesce(f.date_key, n.date_key) as date_key
from fact f
full outer join national n using (date_key)
where f.accesses is distinct from n.accesses
