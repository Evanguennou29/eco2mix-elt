-- Staging model for eco2mix-regional-tr: typed, renamed to English
-- snake_case, deduplicated on (timestamp, region). Only one source dataset
-- is in scope for the regions (no consolidated/definitive regional
-- dataset), so the dedup rule mainly guards against a partition being
-- re-ingested with revised values, not competing sources.
--
-- Long format, like stg_national: one row per (timestamp, region, filiere).
-- The regional dataset does not split thermal generation into oil/coal/gas
-- like the national one does, and has no taux_co2 signal at all — which is
-- exactly why regional carbon intensity has to stay an estimate downstream
-- (documented as a known limitation in the README).

with regional_tr as (
    select * from {{ source('raw', 'regional_tr') }}
),

typed as (
    select
        cast(date_heure as timestamptz) as timestamp_utc,
        cast(date as date) as local_date,
        cast(heure as time) as local_time,
        code_insee_region as region_insee_code,
        libelle_region as region_name,
        case nature
            when 'Données temps réel' then 'real_time'
            when 'Données consolidées' then 'consolidated'
            when 'Données définitives' then 'definitive'
            else lower(nature)
        end as data_quality,
        cast(consommation as double) as consumption_mw,
        cast(ech_physiques as double) as net_exchanges_mw,
        cast(thermique as double) as thermal,
        cast(nucleaire as double) as nuclear,
        cast(eolien as double) as wind,
        cast(solaire as double) as solar,
        cast(hydraulique as double) as hydro,
        cast(pompage as double) as pumped_hydro,
        cast(bioenergies as double) as bioenergy
    from regional_tr
),

ranked as (
    select
        *,
        row_number() over (
            partition by timestamp_utc, region_insee_code
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
    on thermal, nuclear, wind, solar, hydro, pumped_hydro, bioenergy
    into
        name filiere
        value production_mw
)

select
    cast(timestamp_utc at time zone 'UTC' as varchar)
        || '|' || region_insee_code || '|' || filiere as regional_id,
    timestamp_utc,
    local_date,
    local_time,
    region_insee_code,
    region_name,
    data_quality,
    consumption_mw,
    net_exchanges_mw,
    filiere,
    production_mw
from unpivoted
