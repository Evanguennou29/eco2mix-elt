"""Definitions of the three ODRE Explore v2.1 datasets ingested by the pipeline.

Field names and shapes come from the real API responses under
https://opendata.reseaux-energies.fr/api/explore/v2.1/catalog/datasets/<id>/records.
`taux_co2` (the national carbon intensity signal, in gCO2/kWh) is only
published on the national datasets, not the regional one — this is why
regional carbon intensity has to stay an estimate downstream, documented as
a known limitation in the README.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DatasetSpec:
    """One ODRE dataset: its id, the field used to filter by day, and the
    subset of API fields the pipeline retains."""

    dataset_id: str
    date_field: str
    fields: tuple[str, ...]


NATIONAL_FIELDS: tuple[str, ...] = (
    "date",
    "heure",
    "date_heure",
    "nature",
    "consommation",
    "fioul",
    "charbon",
    "gaz",
    "nucleaire",
    "eolien",
    "solaire",
    "hydraulique",
    "pompage",
    "bioenergies",
    "ech_physiques",
    "taux_co2",
)

REGIONAL_FIELDS: tuple[str, ...] = (
    "code_insee_region",
    "libelle_region",
    "date",
    "heure",
    "date_heure",
    "nature",
    "consommation",
    "thermique",
    "nucleaire",
    "eolien",
    "solaire",
    "hydraulique",
    "pompage",
    "bioenergies",
    "ech_physiques",
)

DATASETS: dict[str, DatasetSpec] = {
    "eco2mix-national-tr": DatasetSpec(
        dataset_id="eco2mix-national-tr",
        date_field="date",
        fields=NATIONAL_FIELDS,
    ),
    "eco2mix-national-cons-def": DatasetSpec(
        dataset_id="eco2mix-national-cons-def",
        date_field="date",
        fields=NATIONAL_FIELDS,
    ),
    "eco2mix-regional-tr": DatasetSpec(
        dataset_id="eco2mix-regional-tr",
        date_field="date",
        fields=REGIONAL_FIELDS,
    ),
}
