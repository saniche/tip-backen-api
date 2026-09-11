import os

from sqlalchemy import engine_from_config, pool

from alembic import context
from database import Base


def run_migrations_offline() -> None:
    url = os.environ.get("DATABASE_URL", context.config.get_main_option("sqlalchemy.url"))
    context.configure(url=url, target_metadata=Base.metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    configuration = context.config.get_section(context.config.config_ini_section, {})
    configuration["sqlalchemy.url"] = os.environ.get("DATABASE_URL", configuration["sqlalchemy.url"])
    connectable = engine_from_config(configuration, prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=Base.metadata, render_as_batch=connection.dialect.name == "sqlite")
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
