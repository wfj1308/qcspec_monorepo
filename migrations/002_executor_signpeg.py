"""Create SignPeg executor and ledger tables.

Lightweight migration helper for environments that run Python-based migrations.
For Supabase SQL-first rollout, see `infra/supabase/022_signpeg_executor.sql`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    sql_path = root / "infra" / "supabase" / "022_signpeg_executor.sql"
    return sql_path.read_text(encoding="utf-8")


def apply(connection: Any) -> None:
    """Apply migration SQL to a DB-API compatible connection."""
    sql = load_sql()
    cursor = connection.cursor()
    try:
        cursor.execute(sql)
        connection.commit()
    finally:
        cursor.close()


if __name__ == "__main__":
    raise SystemExit(
        "Run this migration through your migration runner. "
        "Manual SQL is available at infra/supabase/022_signpeg_executor.sql."
    )

