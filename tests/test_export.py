import duckdb
import pyarrow.parquet as pq
import pytest

from eco2mix.export import MART_TABLE_NAMES, export_all, export_mart


@pytest.fixture
def con(tmp_path):
    connection = duckdb.connect(str(tmp_path / "warehouse.duckdb"))
    connection.execute(
        "create table mart_saisonnalite as "
        "select 'winter' as season, 45.5 as avg_carbon_intensity_gco2_kwh "
        "union all select 'summer', 22.0"
    )
    connection.execute(
        "create table mart_intensite_horaire as select 1 as month_number, 0 as hour_of_day"
    )
    connection.execute(
        "create table mart_mix_regional as select '11' as region_insee_code, 'nuclear' as filiere"
    )
    try:
        yield connection
    finally:
        connection.close()


def test_export_mart_writes_a_parquet_file_matching_the_table(con, tmp_path):
    output_dir = tmp_path / "marts"

    path = export_mart(con, "mart_saisonnalite", output_dir)

    assert path == output_dir / "mart_saisonnalite.parquet"
    table = pq.ParquetFile(str(path)).read()
    assert table.column_names == ["season", "avg_carbon_intensity_gco2_kwh"]
    assert sorted(table.column("season").to_pylist()) == ["summer", "winter"]


def test_export_all_writes_every_mart_by_default(con, tmp_path):
    output_dir = tmp_path / "marts"

    paths = export_all(con, output_dir)

    assert {p.name for p in paths} == {f"{name}.parquet" for name in MART_TABLE_NAMES}
    assert all(p.exists() for p in paths)


def test_export_all_can_target_a_subset(con, tmp_path):
    output_dir = tmp_path / "marts"

    paths = export_all(con, output_dir, ["mart_saisonnalite"])

    assert [p.name for p in paths] == ["mart_saisonnalite.parquet"]
    assert list(output_dir.glob("*.parquet")) == paths


def test_export_mart_rerun_overwrites_rather_than_appends(con, tmp_path):
    output_dir = tmp_path / "marts"

    export_mart(con, "mart_saisonnalite", output_dir)
    path = export_mart(con, "mart_saisonnalite", output_dir)

    table = pq.ParquetFile(str(path)).read()
    assert table.num_rows == 2  # not 4: COPY overwrites the file, not appends
