"""Create acceptance/docfinal closure tables.

For Supabase SQL-first rollout, see `infra/supabase/023_acceptance_docfinal.sql`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def load_sql() -> str:
    root = Path(__file__).resolve().parents[1]
    sql_path = root / "infra" / "supabase" / "023_acceptance_docfinal.sql"
    return sql_path.read_text(encoding="utf-8")


def apply(connection: Any) -> None:
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
        "Manual SQL is available at infra/supabase/023_acceptance_docfinal.sql."
    )
