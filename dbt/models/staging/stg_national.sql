-- Staging model for the two national ODRE datasets (eco2mix-national-tr and
-- eco2mix-national-cons-def): typed, renamed to English snake_case, and
-- deduplicated on (timestamp, perimeter) — the same instant can appear in
-- both sources once a period moves from "temps réel" to "consolidée" then
-- "définitive"; the most authoritative nature wins.
--
-- Kept in long ("tidy") format: one row per (timestamp, perimeter, filiere)
-- so `accepted_values` can be tested directly on the filiere column, and so
-- marts can compute each filiere's share of production without pivoting.

with national_tr as (
    select * from {{ source('raw', 'national_tr') }}
),

national_cons_def as (
    select * from {{ source('raw', 'national_cons_def') }}
),

unioned as (
    select * from national_tr
    union all
    select * from national_cons_def
),

typed as (
    select
        cast(date_heure as timestamptz) as timestamp_utc,
        cast(date as date) as local_date,
        cast(heure as time) as local_time,
        perimetre as perimeter,
        case nature
            when 'Données temps réel' then 'real_time'
            when 'Données consolidées' then 'consolidated'
            when 'Données définitives' then 'definitive'
            else lower(nature)
        end as data_quality,
        cast(consommation as double) as consumption_mw,
        cast(taux_co2 as double) as carbon_intensity_gco2_kwh,
        cast(ech_physiques as double) as net_exchanges_mw,
        cast(fioul as double) as oil,
        cast(charbon as double) as coal,
        cast(gaz as double) as gas,
        cast(nucleaire as double) as nuclear,
        cast(eolien as double) as wind,
        cast(solaire as double) as solar,
        cast(hydraulique as double) as hydro,
        cast(pompage as double) as pumped_hydro,
        cast(bioenergies as double) as bioenergy
    from unioned
),

ranked as (
    select
        *,
        row_number() over (
            partition by timestamp_utc, perimeter
            order by
                case data_quality
                    when 'definitive' then 3
                    when 'consolidated' then 2
                    when 'real_time' then 1
                    else 0
                end desc
        ) as _revision_rank
    from typed
),

deduplicated as (
    select * exclude (_revision_rank)
    from ranked
    where _revision_rank = 1
),

unpivoted as (
    unpivot deduplicated
    on oil, coal, gas, nuclear, wind, solar, hydro, pumped_hydro, bioenergy
    into
        name filiere
        value production_mw
)

select
    -- timestamp_utc is cast to varchar via UTC explicitly: implicit ||
    -- casting of a TIMESTAMPTZ renders it in the session's local timezone,
    -- which would make this key depend on where dbt happens to run.
    cast(timestamp_utc at time zone 'UTC' as varchar)
        || '|' || perimeter || '|' || filiere as national_id,
    timestamp_utc,
    local_date,
    local_time,
    perimeter,
    data_quality,
    consumption_mw,
    carbon_intensity_gco2_kwh,
    net_exchanges_mw,
    filiere,
    production_mw
from unpivoted
