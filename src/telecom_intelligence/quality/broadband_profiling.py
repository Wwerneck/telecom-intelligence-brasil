"""Chunked profiling for ANATEL fixed-broadband CSV artifacts."""

import json
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

EXPECTED_COLUMNS = [
    "Ano",
    "Mês",
    "Grupo Econômico",
    "Empresa",
    "CNPJ",
    "Porte da Prestadora",
    "UF",
    "Município",
    "Código IBGE Município",
    "Faixa de Velocidade",
    "Velocidade",
    "Tecnologia",
    "Meio de Acesso",
    "Tipo de Pessoa",
    "Tipo de Produto",
    "Acessos",
]

MEASURE_COLUMNS = {"Acessos"}
GRAIN_COLUMNS = [column for column in EXPECTED_COLUMNS if column not in MEASURE_COLUMNS]


@dataclass(frozen=True)
class BroadbandProfile:
    """Evidence collected without loading the complete source into memory."""

    source_file: str
    delimiter: str
    encoding: str
    columns: list[str]
    rows: int
    chunks: int
    years: list[int]
    months: list[int]
    reference_periods: list[str]
    invalid_years: int
    invalid_months: int
    invalid_ibge_codes: int
    invalid_ufs: int
    non_numeric_speeds: int
    negative_speeds: int
    non_numeric_accesses: int
    negative_accesses: int
    zero_accesses: int
    total_accesses: int
    minimum_accesses: int | None
    maximum_accesses: int | None
    duplicate_grain_rows: int
    null_counts: dict[str, int]
    unique_counts: dict[str, int]


def profile_broadband_csv(path: Path, chunk_size: int = 100_000) -> BroadbandProfile:
    """Profile the semicolon-delimited official CSV incrementally."""
    if chunk_size < 1:
        raise ValueError("chunk_size must be positive")

    reader = pd.read_csv(
        path,
        sep=";",
        encoding="utf-8-sig",
        dtype="string",
        chunksize=chunk_size,
        keep_default_na=True,
        low_memory=False,
    )
    rows = chunks = 0
    invalid_years = invalid_months = invalid_codes = invalid_ufs = 0
    non_numeric_speeds = negative_speeds = 0
    non_numeric_accesses = negative_accesses = zero_accesses = 0
    total_accesses = 0
    minimum_accesses: int | None = None
    maximum_accesses: int | None = None
    duplicate_grain_rows = 0
    null_counts = dict.fromkeys(EXPECTED_COLUMNS, 0)
    distinct = {column: set() for column in EXPECTED_COLUMNS}
    years_seen: set[int] = set()
    months_seen: set[int] = set()
    periods_seen: set[str] = set()
    grain_hashes: set[int] = set()
    valid_ufs = {
        "AC",
        "AL",
        "AP",
        "AM",
        "BA",
        "CE",
        "DF",
        "ES",
        "GO",
        "MA",
        "MT",
        "MS",
        "MG",
        "PA",
        "PB",
        "PR",
        "PE",
        "PI",
        "RJ",
        "RN",
        "RS",
        "RO",
        "RR",
        "SC",
        "SP",
        "SE",
        "TO",
    }

    for frame in reader:
        if frame.columns.tolist() != EXPECTED_COLUMNS:
            raise ValueError(f"Unexpected ANATEL columns: {frame.columns.tolist()}")
        chunks += 1
        rows += len(frame)
        for column in EXPECTED_COLUMNS:
            null_counts[column] += int(frame[column].isna().sum())
            distinct[column].update(frame[column].dropna().unique().tolist())

        year = pd.to_numeric(frame["Ano"], errors="coerce")
        month = pd.to_numeric(frame["Mês"], errors="coerce")
        code = frame["Código IBGE Município"].fillna("")
        speed = pd.to_numeric(
            frame["Velocidade"].str.replace(",", ".", regex=False), errors="coerce"
        )
        accesses = pd.to_numeric(frame["Acessos"], errors="coerce")

        invalid_years += int(year.isna().sum())
        invalid_months += int((month.isna() | ~month.between(1, 12)).sum())
        invalid_codes += int((~code.str.fullmatch(r"\d{7}")).sum())
        invalid_ufs += int((~frame["UF"].isin(valid_ufs)).sum())
        non_numeric_speeds += int(speed.isna().sum())
        negative_speeds += int(speed.lt(0).sum())
        non_numeric_accesses += int(accesses.isna().sum())
        negative_accesses += int(accesses.lt(0).sum())
        zero_accesses += int(accesses.eq(0).sum())

        valid_accesses = accesses.dropna()
        if not valid_accesses.empty:
            total_accesses += int(valid_accesses.sum())
            chunk_min, chunk_max = int(valid_accesses.min()), int(valid_accesses.max())
            minimum_accesses = (
                chunk_min if minimum_accesses is None else min(minimum_accesses, chunk_min)
            )
            maximum_accesses = (
                chunk_max if maximum_accesses is None else max(maximum_accesses, chunk_max)
            )

        years_seen.update(year.dropna().astype(int).tolist())
        months_seen.update(month.dropna().astype(int).tolist())
        valid_period = year.notna() & month.between(1, 12)
        periods_seen.update(
            year[valid_period].astype(int).astype(str)
            + "-"
            + month[valid_period].astype(int).astype(str).str.zfill(2)
        )

        hashes = pd.util.hash_pandas_object(frame[GRAIN_COLUMNS], index=False).astype("uint64")
        for value in hashes.tolist():
            if value in grain_hashes:
                duplicate_grain_rows += 1
            else:
                grain_hashes.add(value)

    return BroadbandProfile(
        source_file=str(path),
        delimiter=";",
        encoding="utf-8-sig",
        columns=EXPECTED_COLUMNS,
        rows=rows,
        chunks=chunks,
        years=sorted(years_seen),
        months=sorted(months_seen),
        reference_periods=sorted(periods_seen),
        invalid_years=invalid_years,
        invalid_months=invalid_months,
        invalid_ibge_codes=invalid_codes,
        invalid_ufs=invalid_ufs,
        non_numeric_speeds=non_numeric_speeds,
        negative_speeds=negative_speeds,
        non_numeric_accesses=non_numeric_accesses,
        negative_accesses=negative_accesses,
        zero_accesses=zero_accesses,
        total_accesses=total_accesses,
        minimum_accesses=minimum_accesses,
        maximum_accesses=maximum_accesses,
        duplicate_grain_rows=duplicate_grain_rows,
        null_counts=null_counts,
        unique_counts={column: len(values) for column, values in distinct.items()},
    )


def write_broadband_profile(
    path: Path, output_path: Path, chunk_size: int = 100_000
) -> BroadbandProfile:
    """Profile an artifact and persist its auditable JSON summary."""
    profile = profile_broadband_csv(path, chunk_size)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(asdict(profile), ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return profile
