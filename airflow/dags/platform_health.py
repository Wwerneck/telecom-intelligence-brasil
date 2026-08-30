"""Minimal DAG proving the orchestration layer can load project code."""

from datetime import datetime

from airflow.decorators import dag, task


@dag(
    dag_id="platform_health",
    start_date=datetime(2025, 1, 1),
    schedule="@daily",
    catchup=False,
    tags=["platform", "health"],
)
def platform_health() -> None:
    """Run a side-effect-free platform health check."""

    @task
    def verify_runtime() -> dict[str, str]:
        return {"status": "healthy", "check": "airflow_runtime"}

    verify_runtime()


platform_health()
