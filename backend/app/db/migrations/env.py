from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool, text

from app.config import get_settings
from app.db.base import Base
import app.models  # noqa: F401 - registers mapped tables


config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)
config.set_main_option("sqlalchemy.url", get_settings().database_url_direct.replace("%", "%%"))
target_metadata = Base.metadata


def include_vector_schema(connection) -> None:
    extension_schema = connection.scalar(text("SELECT n.nspname FROM pg_extension e JOIN pg_namespace n ON n.oid=e.extnamespace WHERE e.extname='vector'"))
    current_schema = connection.scalar(text("SELECT current_schema()"))
    if extension_schema and current_schema and extension_schema != current_schema:
        quote = connection.dialect.identifier_preparer.quote
        connection.exec_driver_sql(f"SET search_path TO {quote(current_schema)}, {quote(extension_schema)}, public")


def run_migrations_offline() -> None:
    context.configure(url=get_settings().database_url_direct, target_metadata=target_metadata, literal_binds=True, dialect_opts={"paramstyle": "named"})
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    supplied_connection = config.attributes.get("connection")
    if supplied_connection is not None:
        include_vector_schema(supplied_connection)
        context.configure(connection=supplied_connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()
        return

    connectable = engine_from_config(config.get_section(config.config_ini_section, {}), prefix="sqlalchemy.", poolclass=pool.NullPool)
    with connectable.connect() as connection:
        include_vector_schema(connection)
        connection.commit()
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
