"""Chart builders for the eco2mix dashboard.

Every function here takes a pandas DataFrame already loaded from one of
the versioned marts under data/marts/ and returns an Altair chart. Nothing
in this module reads a file or talks to a database — main.py owns that,
so these stay easy to reason about and reuse.
"""

from __future__ import annotations

import altair as alt
import pandas as pd

SEASON_ORDER = ["winter", "spring", "summer", "autumn"]

MONTH_LABELS = {
    1: "Jan",
    2: "Feb",
    3: "Mar",
    4: "Apr",
    5: "May",
    6: "Jun",
    7: "Jul",
    8: "Aug",
    9: "Sep",
    10: "Oct",
    11: "Nov",
    12: "Dec",
}
MONTH_ORDER = [MONTH_LABELS[m] for m in sorted(MONTH_LABELS)]


def hourly_intensity_heatmap(mart_intensite_horaire: pd.DataFrame) -> alt.Chart:
    """Month x hour heatmap of average national carbon intensity."""
    df = mart_intensite_horaire.copy()
    df["month_label"] = df["month_number"].map(MONTH_LABELS)

    return (
        alt.Chart(df)
        .mark_rect()
        .encode(
            x=alt.X("hour_of_day:O", title="Hour of day (local time)"),
            y=alt.Y("month_label:O", title="Month", sort=MONTH_ORDER),
            color=alt.Color(
                "avg_carbon_intensity_gco2_kwh:Q",
                title="gCO2/kWh",
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
            ),
            tooltip=[
                alt.Tooltip("month_label:N", title="Month"),
                alt.Tooltip("hour_of_day:O", title="Hour"),
                alt.Tooltip("avg_carbon_intensity_gco2_kwh:Q", title="gCO2/kWh", format=".1f"),
                alt.Tooltip("avg_consumption_mw:Q", title="Avg consumption (MW)", format=",.0f"),
            ],
        )
        .properties(height=320)
    )


def regional_mix_bar(mart_mix_regional: pd.DataFrame) -> alt.Chart:
    """Stacked bar of each filiere's share of generation, one bar per region."""
    return (
        alt.Chart(mart_mix_regional)
        .mark_bar()
        .encode(
            x=alt.X(
                "filiere_share:Q",
                title="Share of regional generation",
                axis=alt.Axis(format="%"),
                stack="normalize",
            ),
            y=alt.Y("region_name:N", title=None, sort="-x"),
            color=alt.Color("filiere:N", title="Filière"),
            order=alt.Order("filiere_share:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("region_name:N", title="Region"),
                alt.Tooltip("filiere:N", title="Filière"),
                alt.Tooltip("filiere_share:Q", title="Share", format=".1%"),
                alt.Tooltip("total_production_mw:Q", title="Total production (MW)", format=",.0f"),
            ],
        )
        .properties(height=420)
    )


def seasonal_intensity_bar(mart_saisonnalite: pd.DataFrame) -> alt.Chart:
    """Bar chart of average national carbon intensity by season."""
    return (
        alt.Chart(mart_saisonnalite)
        .mark_bar()
        .encode(
            x=alt.X("season:N", title="Season", sort=SEASON_ORDER),
            y=alt.Y("avg_carbon_intensity_gco2_kwh:Q", title="Average carbon intensity (gCO2/kWh)"),
            color=alt.Color(
                "avg_carbon_intensity_gco2_kwh:Q",
                legend=None,
                scale=alt.Scale(scheme="redyellowgreen", reverse=True),
            ),
            tooltip=[
                alt.Tooltip("season:N", title="Season"),
                alt.Tooltip("avg_carbon_intensity_gco2_kwh:Q", title="gCO2/kWh", format=".1f"),
                alt.Tooltip("avg_consumption_mw:Q", title="Avg consumption (MW)", format=",.0f"),
                alt.Tooltip("n_observations:Q", title="Readings averaged"),
            ],
        )
        .properties(height=320)
    )
