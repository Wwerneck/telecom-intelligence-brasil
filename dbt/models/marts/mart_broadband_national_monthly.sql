with fact as (
    select * from {{ ref('stg_fact_broadband_accesses') }}
),
population as (
    select
        sum(population) as population,
        max(population_reference_year) as population_reference_year
    from {{ ref('stg_dim_municipality') }}
),
monthly as (
    select
        date_key,
        reference_year,
        reference_month,
        sum(accesses) as accesses,
        sum(case when access_medium = 'Fibra' then accesses else 0 end) as fiber_accesses,
        sum(case when speed_range = '> 34Mbps' then accesses else 0 end) as high_speed_accesses,
        count(distinct municipality_id) as municipalities_with_access,
        count(distinct company_cnpj) as companies
    from fact
    group by 1, 2, 3
)
select
    m.*,
    p.population,
    p.population_reference_year,
    m.accesses::numeric / nullif(p.population, 0) * 100 as accesses_per_100_inhabitants,
    m.fiber_accesses::numeric / nullif(m.accesses, 0) * 100 as fiber_share_pct,
    m.high_speed_accesses::numeric / nullif(m.accesses, 0) * 100 as high_speed_share_pct,
    (m.accesses::numeric / nullif(lag(m.accesses) over (order by m.date_key), 0) - 1) * 100
        as accesses_month_over_month_pct
from monthly m
cross join population p
