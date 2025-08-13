from __future__ import annotations
from logging.config import fileConfig
from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app.core.config import settings
from app.db.base import Base
from app.models import *  # noqa: F401

# Fichier de config Alembic
config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Métadonnées des modèles (tables)
target_metadata = Base.metadata

def get_url() -> str:
    # Récupère l'URL de la base depuis .env via pydantic-settings
    return settings.DATABASE_URL

def run_migrations_offline() -> None:
    # Mode "offline" : exécute les migrations sans connexion live (génère du SQL)
    context.configure(
        url=get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()

def do_run_migrations(connection: Connection) -> None:
    # Applique les migrations avec une connexion active
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()

async def run_migrations_online() -> None:
    # Crée un moteur async et exécute do_run_migrations dans un contexte sync
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
        url=get_url(),
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()

def run_migrations() -> None:
    # Choisit online/offline selon le mode
    if context.is_offline_mode():
        run_migrations_offline()
    else:
        import asyncio
        asyncio.run(run_migrations_online())

run_migrations()
