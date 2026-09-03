{% test filiere_sum_matches_balance(model, group_by_columns, production_column, consumption_column, net_exchanges_column, tolerance_pct=10) %}
{#-
    Business test: for each group (one instant of the time series), the
    sum of every filiere's production plus the net physical exchanges
    should approach total consumption — production + net_exchanges ≈
    consumption, since net_exchanges is positive when France is a net
    importer (extra supply) and negative when exporting (supply leaving).
    A large gap usually means a filiere is missing from the model, a join
    fanned out, or a unit mismatch — not real transmission loss, which is
    only a few percent.

    consumption_column and net_exchanges_column are read via max() since
    they are constant across every filiere row for the same group (the
    model is in long/tidy format); max() just reads that constant value
    without needing a separate join back to a deduplicated table.

    The test fails (returns rows) when the imbalance exceeds
    tolerance_pct of consumption — dbt tests pass on zero rows returned.
-#}

with grouped as (
    select
        {{ group_by_columns | join(', ') }},
        sum({{ production_column }}) as total_production,
        max({{ consumption_column }}) as consumption,
        max({{ net_exchanges_column }}) as net_exchanges
    from {{ model }}
    group by {{ group_by_columns | join(', ') }}
)

select *
from grouped
where
    consumption != 0
    and abs((total_production + net_exchanges) - consumption) > abs(consumption) * {{ tolerance_pct }} / 100.0

{% endtest %}
