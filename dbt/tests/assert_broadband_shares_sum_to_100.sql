select date_key
from {{ ref('mart_broadband_provider_monthly') }}
group by 1
having abs(sum(market_share_pct) - 100) > 0.000001
