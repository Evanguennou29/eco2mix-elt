"""Interactive Streamlit demo based only on the versioned Parquet marts."""

from __future__ import annotations

from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from charts import (
    MONTH_LABELS,
    SEASON_LABELS,
    SOURCE_LABELS,
    hourly_intensity_heatmap,
    monthly_hour_profile,
    regional_mix_bar,
    regional_mix_donut,
    seasonal_intensity_bar,
)

APP_DIR = Path(__file__).resolve().parent
MARTS_DIR = APP_DIR.parent / "data" / "marts"
INTENSITY = "avg_carbon_intensity_gco2_kwh"

st.set_page_config(
    page_title="Éco2mix · Explorer l'électricité française",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)


@st.cache_data(show_spinner=False)
def load_mart(name: str) -> pd.DataFrame:
    return pd.read_parquet(MARTS_DIR / f"{name}.parquet")


def metric_card(label: str, value: str, detail: str, tone: str = "mint") -> None:
    """A compact, animated summary card with escaped data-driven text."""
    st.markdown(
        f"""
        <div class="metric-card metric-card--{tone}">
          <span class="metric-card__label">{escape(label)}</span>
          <strong class="metric-card__value">{escape(value)}</strong>
          <span class="metric-card__detail">{escape(detail)}</span>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section_intro(kicker: str, title: str) -> None:
    st.markdown(
        f"""
        <div class="section-intro">
          <span class="eyebrow">{escape(kicker)}</span>
          <h2>{escape(title)}</h2>
        </div>
        """,
        unsafe_allow_html=True,
    )


def signal_panel(
    mart: pd.DataFrame, minimum: pd.Series, maximum: pd.Series, season_min: pd.Series
) -> None:
    """Draw a data-driven SVG profile with CSS motion, without a live feed."""
    month = int(minimum["month_number"])
    profile = mart.loc[mart["month_number"] == month].sort_values("hour_of_day")
    low = float(profile[INTENSITY].min())
    span = float(profile[INTENSITY].max()) - low or 1.0
    points = [
        (
            22 + int(row.hour_of_day) * 25,
            200 - (float(getattr(row, INTENSITY)) - low) / span * 160,
        )
        for row in profile.itertuples(index=False)
    ]
    line = " ".join(
        f"{'M' if index == 0 else 'L'} {x:.1f} {y:.1f}" for index, (x, y) in enumerate(points)
    )
    area = f"{line} L {points[-1][0]:.1f} 226 L {points[0][0]:.1f} 226 Z"
    marker_index = profile["hour_of_day"].tolist().index(int(minimum["hour_of_day"]))
    marker_x, marker_y = points[marker_index]
    month_label = escape(MONTH_LABELS[month])
    tape = (
        f"<span>MAXIMUM <b>{maximum[INTENSITY]:.1f} g</b></span>"
        f"<span>AMPLITUDE <b>× {maximum[INTENSITY] / minimum[INTENSITY]:.1f}</b></span>"
        f"<span>{escape(SEASON_LABELS[str(season_min['season'])]).upper()} "
        f"<b>{season_min[INTENSITY]:.1f} g CO₂/kWh</b></span>"
    )
    st.markdown(
        f"""
        <div class="signal">
          <div class="signal__mesh" aria-hidden="true"></div>
          <div class="signal__beam" aria-hidden="true"></div>
          <div class="signal__meta">
            <span>FRANCE · MOYENNES HISTORIQUES</span>
            <span>PROFIL HORAIRE / {month_label.upper()}</span>
          </div>
          <div class="signal__body">
            <div class="signal__stat">
              <span class="signal__label">Intensité minimale</span>
              <div class="signal__number">{minimum[INTENSITY]:.1f}</div>
              <div class="signal__unit">g CO₂ / kWh</div>
              <div class="signal__slot">{month_label} · {int(minimum["hour_of_day"]):02d} h</div>
            </div>
            <div class="signal__chart">
              <svg viewBox="0 0 620 255" role="img"
                   aria-label="Profil moyen de l'intensité carbone par heure en {month_label}">
                <defs>
                  <linearGradient id="signal-area" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#c1ff9b" stop-opacity=".48"/>
                    <stop offset="100%" stop-color="#c1ff9b" stop-opacity="0"/>
                  </linearGradient>
                </defs>
                <path class="signal__baseline" d="M 22 226 L 597 226"/>
                <path class="signal__area" d="{area}"/>
                <path class="signal__line" d="{line}" pathLength="1000"/>
                <line class="signal__marker" x1="{marker_x:.1f}" x2="{marker_x:.1f}"
                      y1="{marker_y:.1f}" y2="226"/>
                <circle class="signal__halo" cx="{marker_x:.1f}" cy="{marker_y:.1f}" r="13"/>
                <circle class="signal__point" cx="{marker_x:.1f}" cy="{marker_y:.1f}" r="5"/>
              </svg>
              <div class="signal__axis">
                <span>00</span><span>06</span><span>12</span><span>18</span><span>23 H</span>
              </div>
            </div>
          </div>
          <div class="signal__foot">
            MOYENNE NATIONALE · {month_label.upper()} · {len(profile)} CRÉNEAUX
          </div>
        </div>
        <div class="signal-tape" aria-label="Quelques repères de la série historique">
          <div class="signal-tape__track">{tape}{tape}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


st.markdown(
    f"<style>{(APP_DIR / 'styles.css').read_text(encoding='utf-8')}</style>", unsafe_allow_html=True
)

hourly = load_mart("mart_intensite_horaire")
regional = load_mart("mart_mix_regional")
seasonal = load_mart("mart_saisonnalite")
cleanest = hourly.loc[hourly[INTENSITY].idxmin()]
dirtiest = hourly.loc[hourly[INTENSITY].idxmax()]
cleanest_season = seasonal.loc[seasonal[INTENSITY].idxmin()]
ratio = dirtiest[INTENSITY] / cleanest[INTENSITY]

signal_panel(hourly, cleanest, dirtiest, cleanest_season)

overview_tab, hourly_tab, regional_tab, seasonal_tab = st.tabs(
    ["Vue d'ensemble", "Heures & mois", "Régions", "Saisons"]
)

with overview_tab:
    section_intro(
        "PANORAMA / FRANCE",
        "Douze mois. Vingt-quatre heures.",
    )
    st.altair_chart(hourly_intensity_heatmap(hourly), width="stretch")
    a, b, c = st.columns(3, gap="medium")
    with a:
        metric_card(
            "Maximum observé",
            f"{dirtiest[INTENSITY]:.1f} g",
            f"{MONTH_LABELS[int(dirtiest['month_number'])]} · {int(dirtiest['hour_of_day']):02d} h",
        )
    with b:
        metric_card(
            "Écart entre extrêmes",
            f"× {ratio:.1f}",
            "Entre les créneaux horaires observés",
            "coral",
        )
    with c:
        metric_card(
            "Saison la moins carbonée",
            SEASON_LABELS[str(cleanest_season["season"])],
            f"{cleanest_season[INTENSITY]:.1f} g CO₂/kWh en moyenne",
            "gold",
        )

with hourly_tab:
    section_intro(
        "PROFIL / NATIONAL",
        "Heures & mois",
    )
    month_col, hour_col = st.columns([1, 2], gap="large")
    month_options = sorted(int(month) for month in hourly["month_number"].unique())
    with month_col:
        month = st.selectbox(
            "Mois",
            month_options,
            index=month_options.index(6) if 6 in month_options else 0,
            format_func=lambda value: MONTH_LABELS[value],
        )
    with hour_col:
        hour = st.slider("Heure de la journée", 0, 23, 13, format="%d h")

    month_data = hourly.loc[hourly["month_number"] == month]
    slot = month_data.loc[month_data["hour_of_day"] == hour].iloc[0]
    month_average = month_data[INTENSITY].mean()
    gap = (slot[INTENSITY] / month_average - 1) * 100
    gap_text = f"{abs(gap):.0f} % {'sous' if gap < 0 else 'au-dessus de'} la moyenne du mois"
    a, b, c = st.columns(3, gap="medium")
    with a:
        metric_card(
            "Créneau choisi", f"{slot[INTENSITY]:.1f} g", f"{MONTH_LABELS[month]} · {hour:02d} h"
        )
    with b:
        metric_card(
            "Moyenne du mois", f"{month_average:.1f} g", "Intensité carbone moyenne", "gold"
        )
    with c:
        metric_card("Écart du créneau", gap_text, "Écart à la moyenne mensuelle", "coral")

    st.markdown("<h3 class='chart-heading'>Profil horaire du mois</h3>", unsafe_allow_html=True)
    st.altair_chart(monthly_hour_profile(hourly, month, hour), width="stretch")
    st.markdown(
        "<h3 class='chart-heading'>Toute l'année, heure par heure</h3>", unsafe_allow_html=True
    )
    st.altair_chart(hourly_intensity_heatmap(hourly), width="stretch")

with regional_tab:
    section_intro(
        "MIX / TERRITOIRES",
        "Production par région",
    )
    regions = sorted(regional["region_name"].unique())
    region = st.selectbox("Région", regions)
    region_data = regional.loc[regional["region_name"] == region]
    leading = region_data.loc[region_data["filiere_share"].idxmax()]
    thermal = region_data.loc[region_data["filiere"] == "thermal", "filiere_share"].sum()

    left, right = st.columns([1.65, 1], gap="large")
    with left:
        st.markdown(
            "<h3 class='chart-heading'>Comparer les 12 régions</h3>", unsafe_allow_html=True
        )
        st.altair_chart(regional_mix_bar(regional, region), width="stretch")
    with right:
        st.markdown(
            "<h3 class='chart-heading'>Détail de la région choisie</h3>", unsafe_allow_html=True
        )
        st.altair_chart(regional_mix_donut(regional, region), width="stretch")
        metric_card(
            "Première filière de production",
            SOURCE_LABELS[str(leading["filiere"])],
            f"{leading['filiere_share']:.0%} de la production de {region}",
        )
        st.caption(f"Part du thermique dans la production régionale : {thermal:.0%}.")
    st.info(
        "Ce graphique décrit la production dans chaque région, pas l'électricité consommée "
        "localement. Il ne mesure pas l'intensité carbone régionale."
    )

with seasonal_tab:
    section_intro(
        "CYCLE / FRANCE",
        "Variations saisonnières",
    )
    seasons = [season for season in SEASON_LABELS if season in set(seasonal["season"])]
    season = st.selectbox("Saison", seasons, format_func=lambda value: SEASON_LABELS[value])
    chosen_season = seasonal.loc[seasonal["season"] == season].iloc[0]
    a, b, c = st.columns(3, gap="medium")
    with a:
        metric_card("Intensité moyenne", f"{chosen_season[INTENSITY]:.1f} g", "CO₂ par kWh", "mint")
    with b:
        metric_card(
            "Consommation moyenne",
            f"{chosen_season['avg_consumption_mw']:,.0f} MW".replace(",", " "),
            "Sur les mesures de cette saison",
            "gold",
        )
    with c:
        metric_card(
            "Mesures agrégées",
            f"{int(chosen_season['n_observations']):,}".replace(",", " "),
            "Observations de la table source",
            "coral",
        )
    st.markdown(
        "<h3 class='chart-heading'>Intensité carbone moyenne par saison</h3>",
        unsafe_allow_html=True,
    )
    st.altair_chart(seasonal_intensity_bar(seasonal, season), width="stretch")
    st.markdown(
        "<div class='data-callout'>"
        f"{escape(SEASON_LABELS[str(cleanest_season['season'])])} "
        f"présente la moyenne nationale la plus basse de cette série "
        f"({cleanest_season[INTENSITY]:.1f} g CO₂/kWh).</div>",
        unsafe_allow_html=True,
    )

with st.expander("À propos des données et des limites"):
    st.markdown(
        "Les graphiques lisent trois fichiers Parquet versionnés dans `data/marts/`. "
        "Ils montrent des **moyennes historiques**, pas des valeurs en direct ni des prévisions. "
        "Les données nationales et régionales n'ont pas nécessairement "
        "la même période de couverture. "
        "La filière « pompage » est affichée séparément de l'hydraulique. "
        "[Source : RTE / ODRÉ](https://opendata.reseaux-energies.fr/) · "
        "[Code et méthode](https://github.com/Evanguennou29/eco2mix-elt)"
    )
