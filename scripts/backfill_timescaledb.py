import os
import sys
import time
import pandas as pd
from datetime import datetime, timezone

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from mylibrary import get_db_conn, init_timescaledb_schema


def backfill(hdf5_path: str) -> int:
    """
    Backfill function is obsolete as we've migrated to TimescaleDB.
    This function is kept for backward compatibility but does nothing.
    """
    print("HDF5 backfill is obsolete. TimescaleDB is now the primary storage.")
    return 0


if __name__ == "__main__":
    print("HDF5 backfill is obsolete. TimescaleDB is now the primary storage.")
