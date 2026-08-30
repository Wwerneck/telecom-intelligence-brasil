with fact as (
    select * from {{ ref('stg_fact_broadband_accesses') }}
),
aggregated as (
    select
        date_key,
        reference_year,
        reference_month,
        municipality_id,
        sum(accesses) as accesses,
        sum(case when access_medium = 'Fibra' then accesses else 0 end) as fiber_accesses,
        count(distinct company_cnpj) as companies,
        sum(source_row_count) as source_row_count
    from fact
    group by 1, 2, 3, 4
)
select
    md5(concat_ws('|', a.date_key::text, a.municipality_id::text)) as municipality_month_id,
    a.date_key,
    a.reference_year,
    a.reference_month,
    a.municipality_id,
    d.ibge_code,
    d.municipality_name,
    d.state_code,
    d.state_name,
    d.region_name,
    d.population,
    d.population_reference_year,
    a.accesses,
    a.fiber_accesses,
    a.companies,
    a.source_row_count,
    a.accesses::numeric / nullif(d.population, 0) * 100 as accesses_per_100_inhabitants,
    a.fiber_accesses::numeric / nullif(a.accesses, 0) * 100 as fiber_share_pct
from aggregated a
inner join {{ ref('stg_dim_municipality') }} d using (municipality_id)
