"""Altair charts for the frozen eco2mix dashboard marts."""

from __future__ import annotations

import altair as alt
import pandas as pd

MONTH_LABELS = {
    1: "Janvier",
    2: "Février",
    3: "Mars",
    4: "Avril",
    5: "Mai",
    6: "Juin",
    7: "Juillet",
    8: "Août",
    9: "Septembre",
    10: "Octobre",
    11: "Novembre",
    12: "Décembre",
}
MONTH_ORDER = list(MONTH_LABELS.values())
SEASON_LABELS = {"winter": "Hiver", "spring": "Printemps", "summer": "Été", "autumn": "Automne"}
SEASON_ORDER = list(SEASON_LABELS.values())
SOURCE_LABELS = {
    "bioenergy": "Bioénergies",
    "hydro": "Hydraulique",
    "nuclear": "Nucléaire",
    "pumped_hydro": "Pompage",
    "solar": "Solaire",
    "thermal": "Thermique",
    "wind": "Éolien",
}
SOURCE_COLORS = {
    "Bioénergies": "#7fa66a",
    "Hydraulique": "#4d9dd2",
    "Nucléaire": "#5666a8",
    "Pompage": "#8bc2da",
    "Solaire": "#e9b85d",
    "Thermique": "#e4846b",
    "Éolien": "#55b6a5",
}
INTENSITY_SCALE = alt.Scale(range=["#43aa9a", "#a9d9bd", "#efd28b", "#dd7566"])


def _chart_style(chart: alt.Chart) -> alt.Chart:
    """Keep all charts readable on the light dashboard background."""
    return (
        chart.configure_view(stroke=None)
        .configure_axis(
            labelColor="#455653",
            titleColor="#455653",
            gridColor="#e6ece8",
            domain=False,
            tickColor="#ccd8d1",
            labelFontSize=12,
            titleFontSize=12,
        )
        .configure_legend(labelColor="#455653", titleColor="#455653", labelFontSize=12)
    )


def hourly_intensity_heatmap(mart: pd.DataFrame) -> alt.Chart:
    """National carbon intensity, with readable month and hour tooltips."""
    df = mart.copy()
    df["month_label"] = df["month_number"].map(MONTH_LABELS)
    chart = (
        alt.Chart(df)
        .mark_rect(cornerRadius=3, stroke="#f6f8f5", strokeWidth=2)
        .encode(
            x=alt.X("hour_of_day:O", title="Heure locale", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("month_label:N", title=None, sort=MONTH_ORDER),
            color=alt.Color(
                "avg_carbon_intensity_gco2_kwh:Q",
                title="g CO₂/kWh",
                scale=INTENSITY_SCALE,
            ),
            tooltip=[
                alt.Tooltip("month_label:N", title="Mois"),
                alt.Tooltip("hour_of_day:O", title="Heure"),
                alt.Tooltip(
                    "avg_carbon_intensity_gco2_kwh:Q", title="Intensité (g CO₂/kWh)", format=".1f"
                ),
                alt.Tooltip(
                    "avg_consumption_mw:Q", title="Consommation moyenne (MW)", format=",.0f"
                ),
            ],
        )
        .properties(height=360)
    )
    return _chart_style(chart)


def monthly_hour_profile(mart: pd.DataFrame, month: int, hour: int) -> alt.Chart:
    """Hourly trend for the chosen month, with the chosen hour emphasized."""
    df = mart.loc[mart["month_number"] == month].copy()
    df["selected"] = df["hour_of_day"] == hour
    base = alt.Chart(df).encode(
        x=alt.X("hour_of_day:Q", title="Heure locale", scale=alt.Scale(domain=[0, 23])),
        y=alt.Y("avg_carbon_intensity_gco2_kwh:Q", title="g CO₂/kWh", scale=alt.Scale(zero=False)),
    )
    area = base.mark_area(color="#9dd9cf", opacity=0.27)
    line = base.mark_line(color="#177d72", strokeWidth=3)
    points = base.transform_filter(alt.datum.selected).mark_circle(
        color="#e17b63", size=190, stroke="white", strokeWidth=3
    )
    return _chart_style(alt.layer(area, line, points).properties(height=240))


def regional_mix_bar(mart: pd.DataFrame, selected_region: str) -> alt.Chart:
    """All regional generation mixes, dimming unselected regions."""
    df = mart.copy()
    df["source_label"] = df["filiere"].map(SOURCE_LABELS)
    df["selected"] = df["region_name"] == selected_region
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusEnd=3)
        .encode(
            x=alt.X(
                "filiere_share:Q",
                title="Part de la production régionale",
                axis=alt.Axis(format="%"),
                stack="normalize",
            ),
            y=alt.Y("region_name:N", title=None, sort="-x"),
            color=alt.Color(
                "source_label:N",
                title="Filière",
                scale=alt.Scale(domain=list(SOURCE_COLORS), range=list(SOURCE_COLORS.values())),
            ),
            opacity=alt.condition("datum.selected", alt.value(1), alt.value(0.38)),
            order=alt.Order("filiere_share:Q", sort="descending"),
            tooltip=[
                alt.Tooltip("region_name:N", title="Région"),
                alt.Tooltip("source_label:N", title="Filière"),
                alt.Tooltip("filiere_share:Q", title="Part", format=".1%"),
            ],
        )
        .properties(height=445)
    )
    return _chart_style(chart)


def regional_mix_donut(mart: pd.DataFrame, selected_region: str) -> alt.Chart:
    """Detailed mix for a single region."""
    df = mart.loc[mart["region_name"] == selected_region].copy()
    df["source_label"] = df["filiere"].map(SOURCE_LABELS)
    chart = (
        alt.Chart(df)
        .mark_arc(innerRadius=73, outerRadius=120, stroke="white", strokeWidth=2)
        .encode(
            theta=alt.Theta("filiere_share:Q", stack=True),
            color=alt.Color(
                "source_label:N",
                title="Filière",
                scale=alt.Scale(domain=list(SOURCE_COLORS), range=list(SOURCE_COLORS.values())),
            ),
            tooltip=[
                alt.Tooltip("source_label:N", title="Filière"),
                alt.Tooltip("filiere_share:Q", title="Part", format=".1%"),
            ],
        )
        .properties(height=310)
    )
    return _chart_style(chart)


def seasonal_intensity_bar(mart: pd.DataFrame, selected_season: str) -> alt.Chart:
    """Seasonal national intensity, highlighting the selected season."""
    df = mart.copy()
    df["season_label"] = df["season"].map(SEASON_LABELS)
    df["selected"] = df["season"] == selected_season
    chart = (
        alt.Chart(df)
        .mark_bar(cornerRadiusTopLeft=7, cornerRadiusTopRight=7)
        .encode(
            x=alt.X("season_label:N", title=None, sort=SEASON_ORDER),
            y=alt.Y("avg_carbon_intensity_gco2_kwh:Q", title="Intensité moyenne (g CO₂/kWh)"),
            color=alt.condition("datum.selected", alt.value("#177d72"), alt.value("#9bc9bf")),
            tooltip=[
                alt.Tooltip("season_label:N", title="Saison"),
                alt.Tooltip(
                    "avg_carbon_intensity_gco2_kwh:Q", title="Intensité (g CO₂/kWh)", format=".1f"
                ),
                alt.Tooltip(
                    "avg_consumption_mw:Q", title="Consommation moyenne (MW)", format=",.0f"
                ),
                alt.Tooltip("n_observations:Q", title="Mesures agrégées", format=",.0f"),
            ],
        )
        .properties(height=330)
    )
    return _chart_style(chart)
