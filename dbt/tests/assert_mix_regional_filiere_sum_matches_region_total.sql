-- Business test (SPEC.md: "la somme des filières doit approcher la
-- production totale à une tolérance près"), expressed directly on the
-- mart: for every region, summing total_production_mw across its filiere
-- rows must equal region_total_production_mw — computed via a separate
-- aggregation in mart_mix_regional.sql, then joined back, so this is a
-- real cross-check rather than a tautology. A mismatch here means the
-- mart's join or grouping broke, not a physical-world discrepancy (unlike
-- the staging-level filiere_sum_matches_balance test, this compares two
-- numbers derived from the exact same source rows).
--
-- Passes on zero rows returned; a tiny floating-point tolerance (1 MW)
-- absorbs rounding, not real disagreement.

select
    region_insee_code,
    sum(total_production_mw) as summed_filiere_total,
    max(region_total_production_mw) as region_total_production_mw
from {{ ref('mart_mix_regional') }}
group by region_insee_code
having abs(sum(total_production_mw) - max(region_total_production_mw)) > 1
