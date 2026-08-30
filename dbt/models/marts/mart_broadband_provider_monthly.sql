with aggregated as (
    select
        date_key,
        reference_year,
        reference_month,
        economic_group,
        company_name,
        company_cnpj,
        provider_size,
        sum(accesses) as accesses,
        count(distinct municipality_id) as municipalities
    from {{ ref('stg_fact_broadband_accesses') }}
    group by 1, 2, 3, 4, 5, 6, 7
)
select
    md5(concat_ws('|', date_key::text, company_cnpj, company_name, economic_group)) as provider_month_id,
    *,
    accesses::numeric / nullif(sum(accesses) over (partition by date_key), 0) * 100
        as market_share_pct
from aggregated
