from telecom_intelligence.utils.naming import to_snake_case


def test_to_snake_case_normalizes_portuguese_column_name() -> None:
    assert to_snake_case("  Grupo Econômico  ") == "grupo_economico"


def test_to_snake_case_collapses_separators() -> None:
    assert to_snake_case("Ano  /  Referência") == "ano_referencia"
