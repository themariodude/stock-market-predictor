"""SCRUM-88: Verify database migrations preserve existing records."""

import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text

BACKEND_DIR = Path(__file__).resolve().parents[1]
START_REVISION = "7fbe46751c72"


def run_alembic(database_url: str, *arguments: str) -> None:
    """Run Alembic against the explicitly provided test database."""
    env = os.environ.copy()
    env["DATABASE_URL"] = database_url

    subprocess.run(
        [sys.executable, "-m", "alembic", *arguments],
        cwd=BACKEND_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def test_migrations_preserve_existing_data():
    """Verify existing records survive an upgrade to head."""
    database_url = os.getenv("MIGRATION_TEST_DATABASE_URL")

    if not database_url:
        pytest.skip("Isolated migration test database is not configured.")

    if "migration_preservation_test" not in database_url:
        pytest.fail("Refusing to use a database not designated for migration tests.")

    engine = create_engine(database_url)

    try:
        with engine.connect() as connection:
            existing_tables = connection.execute(
                text("""
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public'
                    AND table_type = 'BASE TABLE'
                """)
            ).scalar_one()

        if existing_tables:
            pytest.fail("Migration test database must start empty.")

        run_alembic(database_url, "upgrade", START_REVISION)

        with engine.begin() as connection:
            connection.execute(
                text("""
                    INSERT INTO data_source_status
                    (id, source, source_key, last_attempt_at,
                     consecutive_failures)
                    VALUES
                    (1, 'FRED', 'SCRUM88_TEST',
                     '2026-10-01 12:00:00+00', 0)
                """)
            )

        run_alembic(database_url, "upgrade", "head")

        with engine.connect() as connection:
            row = connection.execute(
                text("""
                    SELECT source, source_key, consecutive_failures
                    FROM data_source_status
                    WHERE id = 1
                """)
            ).one()

        assert row.source == "FRED"
        assert row.source_key == "SCRUM88_TEST"
        assert row.consecutive_failures == 0

    finally:
        engine.dispose()
