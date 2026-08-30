import json
from pathlib import Path

from telecom_intelligence.quality.profiling import (
    flatten_records,
    load_json_records,
    municipality_quality_issues,
    profile_columns,
    write_municipality_profile,
)


def municipality(code: int = 5200050, uf: str = "GO") -> dict:
    return {
        "id": code,
        "nome": "Abadia de Goiás",
        "microrregiao": None,
        "regiao-imediata": {
            "regiao-intermediaria": {"UF": {"sigla": uf, "regiao": {"nome": "Centro-Oeste"}}}
        },
    }


def test_column_profile_reports_source_nulls() -> None:
    frame = flatten_records([municipality()])
    profile = profile_columns(frame).set_index("column")

    assert profile.loc["microrregiao", "null_count"] == 1
    assert profile.loc["nome", "unique_count"] == 1


def test_municipality_rules_flag_invalid_uf() -> None:
    issues = municipality_quality_issues(flatten_records([municipality(5200050, "XX")]))

    assert issues["reason"].tolist() == ["invalid_uf"]


def test_profile_writes_auditable_artifacts(tmp_path: Path) -> None:
    raw_path = tmp_path / "municipios.json"
    raw_path.write_text(json.dumps([municipality()]), encoding="utf-8")

    artifacts = write_municipality_profile(raw_path, tmp_path / "reports")
    summary = json.loads(artifacts.summary.read_text(encoding="utf-8"))

    assert summary["shape"]["rows"] == 1
    assert artifacts.missing_values.exists()
    assert artifacts.duplicate_keys.read_text(encoding="utf-8").strip() == "id,nome"


def test_loader_rejects_non_record_json(tmp_path: Path) -> None:
    raw_path = tmp_path / "invalid.json"
    raw_path.write_text('{"id": 1}', encoding="utf-8")

    try:
        load_json_records(raw_path)
    except ValueError as error:
        assert "array of objects" in str(error)
    else:
        raise AssertionError("Expected ValueError")
