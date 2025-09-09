#!/usr/bin/env python3
"""Simple migration smoke test.

Runs run_db_migrations() and verifies existence of required tables/columns.
Database connectivity is taken from environment variables (.env via Compose).
"""
import os
import sys

# Ensure project root on sys.path for local execution / hooks
ROOT = os.path.dirname(os.path.dirname(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from mylibrary import get_db_conn, run_db_migrations


REQUIRED_TABLES = {
    'users': ['id', 'email', 'email_hash', 'email_salt', 'created_at'],
    'otp_codes': ['id', 'user_id', 'otp_hash', 'salt', 'expires_at'],
    'notification_profiles': ['id', 'user_id', 'name', 'type', 'ci_list', 'apprise_urls', 'apprise_urls_hash', 'apprise_urls_salt', 'email_notifications', 'email_address', 'unsubscribe_token'],
}


def table_exists(cur, name: str) -> bool:
    cur.execute("SELECT to_regclass(%s)", (f'public.{name}',))
    return cur.fetchone()[0] is not None


def column_exists(cur, table: str, column: str) -> bool:
    cur.execute(
        """
        SELECT 1 FROM information_schema.columns
        WHERE table_schema='public' AND table_name=%s AND column_name=%s
        """,
        (table, column),
    )
    return cur.fetchone() is not None


def main() -> int:
    try:
        # Run migrations
        run_db_migrations()

        # Verify schema
        with get_db_conn() as conn, conn.cursor() as cur:
            for table, cols in REQUIRED_TABLES.items():
                if not table_exists(cur, table):
                    print(f"ERROR: missing table {table}")
                    return 1
                for col in cols:
                    if not column_exists(cur, table, col):
                        print(f"ERROR: missing column {table}.{col}")
                        return 1
        print("OK: migrations passed and schema verified")
        return 0
    except Exception as e:
        if "could not translate host name" in str(e) or "Connection refused" in str(e):
            print("SKIP: Database not available for migration test")
            return 0
        print(f"ERROR: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())


