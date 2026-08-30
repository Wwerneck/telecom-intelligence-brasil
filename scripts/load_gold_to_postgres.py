"""Load content-addressed Gold Parquets into PostgreSQL source tables for dbt."""

import csv
import io
import os
from pathlib import Path

import pandas as pd
import psycopg
import pyarrow as pa
import pyarrow.parquet as pq


def sql_type(data_type: pa.DataType) -> str:
    if pa.types.is_integer(data_type):
        return "bigint"
    if pa.types.is_floating(data_type):
        return "double precision"
    if pa.types.is_boolean(data_type):
        return "boolean"
    if pa.types.is_date(data_type):
        return "date"
    if pa.types.is_timestamp(data_type):
        return "timestamp with time zone" if data_type.tz else "timestamp"
    return "text"


def quote(identifier: str) -> str:
    return '"' + identifier.replace('"', '""') + '"'


def load_parquets(
    connection: psycopg.Connection, schema: str, table_name: str, paths: list[Path]
) -> int:
    """Replace one table and stream Parquet row groups through PostgreSQL COPY."""
    if not paths:
        raise FileNotFoundError(f"No Parquets supplied for {schema}.{table_name}")
    arrow_schema = pq.read_schema(paths[0])
    columns = arrow_schema.names
    definitions = ", ".join(f"{quote(field.name)} {sql_type(field.type)}" for field in arrow_schema)
    qualified = f"{quote(schema)}.{quote(table_name)}"
    with connection.cursor() as cursor:
        cursor.execute(f"DROP TABLE IF EXISTS {qualified}")
        cursor.execute(f"CREATE TABLE {qualified} ({definitions})")
        column_sql = ", ".join(quote(column) for column in columns)
        rows = 0
        copy_sql = f"COPY {qualified} ({column_sql}) FROM STDIN WITH (FORMAT CSV, NULL '\\N')"
        with cursor.copy(copy_sql) as copy:
            for path in paths:
                parquet = pq.ParquetFile(path)
                if parquet.schema_arrow.names != columns:
                    raise ValueError(f"Schema drift across Parquets: {path}")
                for batch in parquet.iter_batches(batch_size=50_000):
                    frame = batch.to_pandas()
                    buffer = io.StringIO()
                    frame.to_csv(
                        buffer,
                        index=False,
                        header=False,
                        na_rep="\\N",
                        quoting=csv.QUOTE_MINIMAL,
                        lineterminator="\n",
                    )
                    copy.write(buffer.getvalue())
                    rows += len(frame)
        cursor.execute(f"ANALYZE {qualified}")
    return rows


def populated_municipality_dimension(paths: list[Path]) -> Path:
    for path in sorted(paths, reverse=True):
        population = pd.read_parquet(path, columns=["population"])
        if population["population"].notna().all():
            return path
    raise FileNotFoundError("No populated municipality dimension found")


def main() -> None:
    connection = psycopg.connect(
        host=os.getenv("POSTGRES_HOST", "localhost"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        dbname=os.getenv("POSTGRES_DB", "telecom"),
        user=os.getenv("POSTGRES_USER", "telecom"),
        password=os.environ["POSTGRES_PASSWORD"],
    )
    try:
        fact_paths = sorted(
            Path("data/gold/fact_broadband_accesses").glob("year=*/month=*/*.parquet")
        )
        municipality = populated_municipality_dimension(
            list(Path("data/gold/dim_municipality").glob("*.parquet"))
        )
        dates = list(Path("data/gold/dim_date/source=fixed_broadband_accesses").glob("*.parquet"))
        counts = {
            "fact_broadband_accesses": load_parquets(
                connection, "gold", "fact_broadband_accesses", fact_paths
            ),
            "dim_municipality": load_parquets(
                connection, "gold", "dim_municipality", [municipality]
            ),
            "dim_date": load_parquets(connection, "gold", "dim_date", dates),
        }
        connection.commit()
        print(counts)
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


if __name__ == "__main__":
    main()
