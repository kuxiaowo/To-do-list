"""Final Todo IP-data cutover after the Accounts/Caddy overlap period.

Dry-run is the default.  For production, back up the database first and run
with --apply only after the Accounts index has been checked for one full cycle.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from server import get_db  # noqa: E402


def existing_tables(conn) -> set[str]:
    return {
        row["name"] for row in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
    }


def columns(conn, table: str) -> set[str]:
    return {row["name"] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()}


def operations(conn) -> list[str]:
    tables = existing_tables(conn)
    result = []
    for table in ("visit_logs", "registration_attempt_logs"):
        if table in tables:
            result.append(f"DROP TABLE {table}")
    for table in ("operation_logs", "installer_download_logs"):
        if table in tables and "ip" in columns(conn, table):
            if table == "installer_download_logs":
                result.append("DROP INDEX IF EXISTS idx_installer_download_logs_ip")
            result.append(f"ALTER TABLE {table} DROP COLUMN ip")
    if "app_settings" in tables:
        result.append(
            "DELETE FROM app_settings WHERE key='registration_ip_attempt_limit'"
        )
    return result


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="Permanently remove legacy IP data")
    args = parser.parse_args()
    with get_db() as conn:
        statements = operations(conn)
        for statement in statements:
            print(statement)
        if args.apply:
            for statement in statements:
                conn.execute(statement)
            conn.commit()
            print("Legacy Todo IP data removed")
        else:
            print("Dry run only; database unchanged")


if __name__ == "__main__":
    main()
