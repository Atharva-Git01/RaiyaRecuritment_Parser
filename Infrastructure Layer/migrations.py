from __future__ import annotations

from pathlib import Path
from typing import List

from app.config import get_settings
from app import repositories
from app.saas_db import get_db_connection


def _ensure_schema_migrations_table() -> None:
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version VARCHAR(100) PRIMARY KEY,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        conn.commit()


def _applied_versions() -> set[str]:
    _ensure_schema_migrations_table()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('SELECT version FROM schema_migrations')
        return {row[0] for row in cursor.fetchall()}


def apply_migrations() -> List[str]:
    settings = get_settings()
    _ensure_schema_migrations_table()
    applied = _applied_versions()
    executed: List[str] = []
    migration_files = sorted(Path(settings.migrations_dir).glob('*.sql'))
    import mysql.connector
    for migration_file in migration_files:
        version = migration_file.name
        if version in applied:
            continue
        script = migration_file.read_text(encoding='utf-8-sig')
        statements: List[str] = []
        current_stmt: List[str] = []
        for line in script.splitlines():
            stripped = line.strip()
            if stripped.startswith('--') or not stripped:
                continue
            current_stmt.append(line)
            if stripped.endswith(';'):
                statements.append('\n'.join(current_stmt))
                current_stmt = []
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SET FOREIGN_KEY_CHECKS = 0;')
            for stmt in statements:
                if not stmt.strip():
                    continue
                modified_stmt = stmt.replace('ADD COLUMN IF NOT EXISTS', 'ADD COLUMN')
                try:
                    cursor.execute(modified_stmt)
                except mysql.connector.Error as exc:
                    if exc.errno in (1050, 1054, 1060, 1061, 1091, 1831):
                        pass
                    else:
                        raise
            cursor.execute('INSERT INTO schema_migrations (version) VALUES (%s)', (version,))
            cursor.execute('SET FOREIGN_KEY_CHECKS = 1;')
            conn.commit()
        executed.append(version)
    return executed


def ensure_runtime_ready() -> dict:
    settings = get_settings()
    settings.validate_runtime()
    applied = []
    if settings.auto_apply_migrations:
        applied = apply_migrations()
    defaults = repositories.bootstrap_defaults()
    return {'applied_migrations': applied, 'defaults': defaults}

