import os
import sys
import time
import h5py
import pandas as pd
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mylibrary import get_db_conn, init_timescaledb_schema


def backfill(hdf5_path: str) -> int:
    if not os.path.exists(hdf5_path):
        print(f"HDF5 nicht gefunden: {hdf5_path}")
        return 0

    init_timescaledb_schema()

    inserted = 0
    batch = []
    batch_size = 5000

    with get_db_conn() as conn, conn.cursor() as cur:
        with h5py.File(hdf5_path, 'r', swmr=True) as f:
            if 'availability' not in f:
                print("Gruppe 'availability' fehlt")
                return 0
            availability = f['availability']
            for ci in availability.keys():
                ci_group = availability[ci]
                for ts_key in ci_group.keys():
                    try:
                        ts = float(ts_key)
                        ds = ci_group[ts_key]
                        val = int(ds[()]) if isinstance(ds, h5py.Dataset) else int(ds)
                        dt = datetime.fromtimestamp(ts, tz=timezone.utc)
                        batch.append((ci, dt, val))
                        if len(batch) >= batch_size:
                            cur.executemany(
                                "INSERT INTO measurements (ci, ts, status) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                                batch,
                            )
                            inserted += cur.rowcount
                            batch.clear()
                    except Exception:
                        continue
            if batch:
                cur.executemany(
                    "INSERT INTO measurements (ci, ts, status) VALUES (%s,%s,%s) ON CONFLICT DO NOTHING",
                    batch,
                )
                inserted += cur.rowcount
                batch.clear()
    return inserted


if __name__ == "__main__":
    hdf5 = sys.argv[1] if len(sys.argv) > 1 else os.getenv('HDF5_PATH', 'data/data.hdf5')
    start = time.time()
    n = backfill(hdf5)
    dur = time.time() - start
    print(f"Backfill fertig: {n} Zeilen in {dur:.1f}s")


