-- Share of each filiere in each region's total generation: the table that
-- answers "does the cleanest hour to consume change by region" — a region
-- leaning on nuclear/hydro/wind looks very different from one leaning on
-- thermal.
--
-- NOTE ON A MISSING COLUMN, for the README's "known limitations" section
-- (lot 6): there is no regional equivalent of stg_national's
-- carbon_intensity_gco2_kwh here, and there never will be from this
-- source. RTE's own taux_co2 signal (gCO2/kWh) is only published on the
-- national datasets (eco2mix-national-tr / -cons-def), not on
-- eco2mix-regional-tr — verified against the real API schema in lot 1/2.
-- A regional carbon intensity would have to be estimated (e.g. from this
-- mart's filiere mix times national or filiere-level emission factors),
-- which this pipeline deliberately does not do: it would be a modelling
-- exercise, not a fact read off ODRE, and is out of scope (see SPEC.md's
-- "no forecasting, no ML" boundary — the same reasoning against inventing
-- numbers the source doesn't give us).

with regional_production as (
    select
        region_insee_code,
        region_name,
        filiere,
        sum(production_mw) as total_production_mw
    from {{ ref('stg_regional') }}
    group by 1, 2, 3
),

regional_totals as (
    select
        region_insee_code,
        sum(total_production_mw) as region_total_production_mw
    from regional_production
    group by 1
)

select
    regional_production.region_insee_code || '-' || regional_production.filiere as mix_regional_id,
    regional_production.region_insee_code,
    regional_production.region_name,
    regional_production.filiere,
    regional_production.total_production_mw,
    regional_totals.region_total_production_mw,
    regional_production.total_production_mw
        / nullif(regional_totals.region_total_production_mw, 0) as filiere_share
from regional_production
inner join regional_totals using (region_insee_code)
order by region_insee_code, filiere
