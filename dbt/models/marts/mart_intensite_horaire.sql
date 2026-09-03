-- Average national carbon intensity by hour of day and by month: the
-- table the README's headline answer ("at what hour should you consume
-- electricity in France to emit the least CO2") is read directly off.
--
-- stg_national is in long format (one row per filiere), but
-- carbon_intensity_gco2_kwh and consumption_mw are constants repeated on
-- every filiere row for a given instant — `select distinct` on those
-- columns alone collapses back to one row per timestamp before averaging,
-- so the hourly/monthly average is not skewed by however many filiere
-- rows happen to exist per instant.

with national_instants as (
    select distinct
        local_date,
        local_time,
        consumption_mw,
        carbon_intensity_gco2_kwh
    from {{ ref('stg_national') }}
),

hourly as (
    select
        extract(month from local_date)::integer as month_number,
        extract(hour from local_time)::integer as hour_of_day,
        avg(carbon_intensity_gco2_kwh) as avg_carbon_intensity_gco2_kwh,
        avg(consumption_mw) as avg_consumption_mw,
        count(*) as n_observations
    from national_instants
    group by 1, 2
)

select
    cast(month_number as varchar) || '-' || cast(hour_of_day as varchar) as intensite_horaire_id,
    month_number,
    hour_of_day,
    avg_carbon_intensity_gco2_kwh,
    avg_consumption_mw,
    n_observations
from hourly
order by month_number, hour_of_day
