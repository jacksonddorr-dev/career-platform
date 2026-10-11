"""Copy every app row from one database into an empty, migrated one (VM SQLite -> Railway Postgres)."""
import sys

from sqlalchemy import create_engine, func, select, text

from app.config import normalize_database_url
from app.models import Base


def copy_database(source_url: str, target_url: str) -> dict[str, int]:
    source = create_engine(normalize_database_url(source_url))
    target = create_engine(normalize_database_url(target_url))
    tables = Base.metadata.sorted_tables
    counts: dict[str, int] = {}
    try:
        with source.connect() as src, target.begin() as dst:
            for table in tables:
                if dst.execute(select(func.count()).select_from(table)).scalar_one():
                    raise ValueError(f"target table {table.name} is not empty; refusing to copy")
            for table in tables:
                rows = [dict(row._mapping) for row in src.execute(select(table))]
                if rows:
                    dst.execute(table.insert(), rows)
                counts[table.name] = len(rows)
            if target.dialect.name == "postgresql":
                for table in tables:
                    dst.execute(text(
                        f"SELECT setval(pg_get_serial_sequence('{table.name}', 'id'), "
                        f"COALESCE(MAX(id), 1), MAX(id) IS NOT NULL) FROM {table.name}"))
    finally:
        source.dispose()
        target.dispose()
    return counts


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: python -m app.copy_db SOURCE_URL TARGET_URL")
    for name, count in copy_database(sys.argv[1], sys.argv[2]).items():
        print(f"{name}: {count}")
