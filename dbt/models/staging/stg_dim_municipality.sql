select
    municipality_id,
    ibge_code,
    municipality_name,
    state_code,
    state_name,
    region_name,
    population,
    population_reference_year
from {{ source('gold', 'dim_municipality') }}
