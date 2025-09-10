#!/usr/bin/env python3
import argparse
import os
import sys
import time
from datetime import datetime, timezone


def find_any_ci(conn):
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT ci
                FROM ci_metadata
                ORDER BY ci
                LIMIT 1
            """)
            row = cur.fetchone()
            return row[0] if row else None
    except Exception:
        return None


def get_latest_status(conn, ci):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT status
            FROM measurements
            WHERE ci = %s
            ORDER BY ts DESC
            LIMIT 1
            """,
            (ci,)
        )
        row = cur.fetchone()
        return int(row[0]) if row is not None else None


def insert_measurement(conn, ci, status, ts=None):
    if ts is None:
        ts = datetime.now(timezone.utc)
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO measurements (ci, ts, status)
            VALUES (%s, %s, %s)
            """,
            (ci, ts, int(status))
        )
    conn.commit()


def simulate_via_db(ci, mode):
    from mylibrary import get_db_conn, send_db_notifications

    # Connect to DB
    with get_db_conn() as conn:
        # Pick CI if not provided
        target_ci = ci
        if not target_ci:
            target_ci = find_any_ci(conn)
            if not target_ci:
                print("Kein CI gefunden (ci_metadata leer?)", file=sys.stderr)
                return 1

        latest = get_latest_status(conn, target_ci)
        # Default to available if unknown
        if latest not in (0, 1):
            latest = 1

        if mode == 'incident':
            # Prev := 1, Now := 0
            prev_status, new_status = 1, 0
        elif mode == 'recovery':
            # Prev := 0, Now := 1
            prev_status, new_status = 0, 1
        else:  # toggle
            prev_status, new_status = latest, 0 if latest == 1 else 1

        # Ensure we create a change edge reliably: write two rows with slight time delta
        ts_prev = datetime.now(timezone.utc)
        insert_measurement(conn, target_ci, prev_status, ts_prev)
        # tiny delay to ensure ordering
        time.sleep(0.25)
        ts_new = datetime.now(timezone.utc)
        insert_measurement(conn, target_ci, new_status, ts_new)

        print(f"Messwerte eingefügt für CI={target_ci}: prev={prev_status}, now={new_status}")

    # Trigger notifications
    processed = send_db_notifications()
    print(f"send_db_notifications() verarbeitet: {processed} Profile")
    return 0


def simulate_via_mock(ci, mode):
    import pandas as pd
    import mylibrary

    # Snapshot real DF
    df = mylibrary.get_data_of_all_cis('')
    if df is None or df.empty:
        print("Keine CI-Daten vorhanden (DF leer)", file=sys.stderr)
        return 1

    # Wähle CI
    target_ci = ci or df.iloc[0]['ci']
    if target_ci not in set(df['ci']):
        print(f"CI '{target_ci}' nicht im DataFrame, wähle ersten Eintrag.")
        target_ci = df.iloc[0]['ci']

    # Setze künstliche Änderung
    idx = df[df['ci'] == target_ci].index
    if mode == 'incident':
        df.loc[idx, 'availability_difference'] = -1
    elif mode == 'recovery':
        df.loc[idx, 'availability_difference'] = 1
    else:
        # toggle: invert current availability to force a change
        current = df.loc[idx, 'current_availability'].iloc[0]
        df.loc[idx, 'availability_difference'] = -1 if int(current) == 1 else 1

    # Monkeypatch get_data_of_all_cis
    original = mylibrary.get_data_of_all_cis
    mylibrary.get_data_of_all_cis = lambda _ignored: df
    try:
        processed = mylibrary.send_db_notifications()
        print(f"[MOCK] send_db_notifications() verarbeitet: {processed} Profile")
    finally:
        mylibrary.get_data_of_all_cis = original
    return 0


def main():
    parser = argparse.ArgumentParser(description="Simuliere Benachrichtigungen bei CI-Ausfall/Wiederherstellung")
    parser.add_argument("--ci", help="CI-ID (optional; wenn leer, wird eine beliebige CI gewählt)")
    parser.add_argument("--mode", choices=["incident", "recovery", "toggle"], default="incident", help="Art der Änderung")
    parser.add_argument("--method", choices=["db", "mock"], default="db", help="Simulationsmethode: echte DB-Einträge oder Mock")
    args = parser.parse_args()

    if args.method == 'db':
        return simulate_via_db(args.ci, args.mode)
    else:
        return simulate_via_mock(args.ci, args.mode)


if __name__ == "__main__":
    sys.exit(main())


