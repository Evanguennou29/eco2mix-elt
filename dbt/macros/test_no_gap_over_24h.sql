{% test no_gap_over_24h(model, column_name, partition_by=none, max_gap_hours=24) %}
{#-
    Business test: no gap greater than max_gap_hours between two
    consecutive readings of the time series, per partition_by (e.g. one
    series per perimeter or per region). ODRE's own revision cadence
    (temps réel -> consolidée -> définitive) makes it easy to accidentally
    end up ingesting a date range with a hole in it; this catches that
    before it reaches a mart.

    The test fails (returns rows) when a gap is found — dbt tests pass on
    zero rows returned.
-#}

with distinct_timestamps as (
    select distinct
        {{ column_name }} as ts
        {%- if partition_by %}, {{ partition_by }} as partition_key{% endif %}
    from {{ model }}
),

ordered as (
    select
        ts,
        {%- if partition_by %}
        partition_key,
        {%- endif %}
        lag(ts) over (
            {%- if partition_by %}partition by partition_key{% endif %}
            order by ts
        ) as previous_ts
    from distinct_timestamps
)

select *
from ordered
where
    previous_ts is not null
    and date_diff('hour', previous_ts, ts) > {{ max_gap_hours }}

{% endtest %}
