from eco2mix.ingest.datasets import DATASETS

EXPECTED_DATASET_IDS = {
    "eco2mix-national-tr",
    "eco2mix-national-cons-def",
    "eco2mix-regional-tr",
}


def test_datasets_cover_the_three_odre_datasets_in_scope():
    assert set(DATASETS) == EXPECTED_DATASET_IDS


def test_each_dataset_filters_by_a_date_field_present_in_its_own_fields():
    for spec in DATASETS.values():
        assert spec.date_field in spec.fields
        assert len(spec.fields) == len(set(spec.fields))


def test_only_national_datasets_carry_the_carbon_intensity_signal():
    assert "taux_co2" in DATASETS["eco2mix-national-tr"].fields
    assert "taux_co2" in DATASETS["eco2mix-national-cons-def"].fields
    assert "taux_co2" not in DATASETS["eco2mix-regional-tr"].fields
