import os
from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

import app.models.macro  # noqa: F401  (registers MacroObservation on Base)
import app.models.source_status  # noqa: F401  (registers DataSourceStatus on Base)
from app.database import Base

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set.")

target_metadata = Base.metadata

# Alembic manages only these tables. Other models on Base (stocks,
# stock_prices) are left untouched until the team adopts migrations for them.
MANAGED_TABLES = {"macro_observations", "data_source_status"}


def include_object(obj, name, type_, reflected, compare_to):
    if type_ == "table":
        return name in MANAGED_TABLES
    table = getattr(obj, "table", None)
    return table is None or table.name in MANAGED_TABLES


def run_migrations_offline() -> None:
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        include_object=include_object,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = create_engine(DATABASE_URL, poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
