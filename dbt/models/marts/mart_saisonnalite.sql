-- National carbon intensity and consumption by (meteorological) season:
-- the table the README's summer/winter gap finding is read off.
--
-- Same long-format collapse as mart_intensite_horaire: distinct on the
-- per-instant constants before averaging, so the season average is not
-- skewed by the number of filiere rows per instant.

with national_instants as (
    select distinct
        local_date,
        consumption_mw,
        carbon_intensity_gco2_kwh
    from {{ ref('stg_national') }}
),

seasoned as (
    select
        case extract(month from local_date)
            when 12 then 'winter'
            when 1 then 'winter'
            when 2 then 'winter'
            when 3 then 'spring'
            when 4 then 'spring'
            when 5 then 'spring'
            when 6 then 'summer'
            when 7 then 'summer'
            when 8 then 'summer'
            when 9 then 'autumn'
            when 10 then 'autumn'
            when 11 then 'autumn'
        end as season,
        consumption_mw,
        carbon_intensity_gco2_kwh
    from national_instants
)

select
    season as saisonnalite_id,
    season,
    avg(carbon_intensity_gco2_kwh) as avg_carbon_intensity_gco2_kwh,
    avg(consumption_mw) as avg_consumption_mw,
    count(*) as n_observations
from seasoned
group by 1, 2
order by
    case season
        when 'winter' then 1
        when 'spring' then 2
        when 'summer' then 3
        when 'autumn' then 4
    end
