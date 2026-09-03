"""eco2mix dashboard — Streamlit.

Reads only the versioned Parquet files under data/marts/: this app never
calls the ODRE API or opens the DuckDB warehouse. That's a deliberate
architecture decision (see SPEC.md) — a demo link that depends on a live
API or a multi-GB warehouse file is a demo link that eventually breaks or
can't be deployed on a free tier; a handful of small, frozen, versioned
Parquet files can't.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import streamlit as st

from charts import MONTH_LABELS, hourly_intensity_heatmap, regional_mix_bar, seasonal_intensity_bar

MARTS_DIR = Path(__file__).resolve().parent.parent / "data" / "marts"

st.set_page_config(page_title="eco2mix — when is French electricity cleanest?", layout="wide")


@st.cache_data
def load_mart(name: str) -> pd.DataFrame:
    return pd.read_parquet(MARTS_DIR / f"{name}.parquet")


st.title("When should you consume electricity in France to emit the least CO2?")
st.caption(
    "A reproducible ELT pipeline over RTE's public eco2mix data — ingestion, dbt staging and "
    "marts, this dashboard. The charts below read three frozen, versioned tables; nothing here "
    "calls a live API."
)

tab_hourly, tab_regional, tab_seasonal = st.tabs(["By hour & month", "By region", "By season"])

with tab_hourly:
    mart_intensite_horaire = load_mart("mart_intensite_horaire")
    cleanest = mart_intensite_horaire.loc[
        mart_intensite_horaire["avg_carbon_intensity_gco2_kwh"].idxmin()
    ]
    dirtiest = mart_intensite_horaire.loc[
        mart_intensite_horaire["avg_carbon_intensity_gco2_kwh"].idxmax()
    ]
    ratio = dirtiest["avg_carbon_intensity_gco2_kwh"] / cleanest["avg_carbon_intensity_gco2_kwh"]

    st.subheader("Carbon intensity by hour of day and month")
    st.altair_chart(hourly_intensity_heatmap(mart_intensite_horaire), use_container_width=True)
    cleanest_month = MONTH_LABELS[int(cleanest["month_number"])]
    dirtiest_month = MONTH_LABELS[int(dirtiest["month_number"])]
    st.success(
        f"**Finding:** the cleanest slot is {cleanest_month}, {int(cleanest['hour_of_day'])}h, "
        f"at {cleanest['avg_carbon_intensity_gco2_kwh']:.0f} gCO2/kWh; the dirtiest is "
        f"{dirtiest_month}, {int(dirtiest['hour_of_day'])}h, at "
        f"{dirtiest['avg_carbon_intensity_gco2_kwh']:.0f} gCO2/kWh — **{ratio:.1f}x higher**. "
        "The answer clearly depends on both the hour and the time of year, not just the hour "
        "alone."
    )

with tab_regional:
    mart_mix_regional = load_mart("mart_mix_regional")
    thermal_share = (
        mart_mix_regional[mart_mix_regional["filiere"] == "thermal"]
        .set_index("region_name")["filiere_share"]
        .fillna(0)
    )
    cleanest_region = thermal_share.idxmin()
    dirtiest_region = thermal_share.idxmax()

    st.subheader("Generation mix by region")
    st.altair_chart(regional_mix_bar(mart_mix_regional), use_container_width=True)
    st.success(
        f"**Finding:** {dirtiest_region} draws {thermal_share[dirtiest_region]:.0%} of its "
        f"generation from thermal plants, versus {thermal_share[cleanest_region]:.0%} in "
        f"{cleanest_region} — the regional generation mix, and so the cleanest hour to "
        "consume, is not the same nationwide."
    )

with tab_seasonal:
    mart_saisonnalite = load_mart("mart_saisonnalite")
    winter = mart_saisonnalite.set_index("season").loc["winter"]
    cleanest_season = mart_saisonnalite.loc[
        mart_saisonnalite["avg_carbon_intensity_gco2_kwh"].idxmin()
    ]
    gap_pct = (
        (winter["avg_carbon_intensity_gco2_kwh"] - cleanest_season["avg_carbon_intensity_gco2_kwh"])
        / cleanest_season["avg_carbon_intensity_gco2_kwh"]
        * 100
    )

    st.subheader("Carbon intensity by season")
    st.altair_chart(seasonal_intensity_bar(mart_saisonnalite), use_container_width=True)
    st.success(
        f"**Finding:** winter averages {winter['avg_carbon_intensity_gco2_kwh']:.0f} gCO2/kWh, "
        f"versus {cleanest_season['avg_carbon_intensity_gco2_kwh']:.0f} in "
        f"{cleanest_season['season']}, the cleanest season — a **{gap_pct:.0f}% gap**."
    )
