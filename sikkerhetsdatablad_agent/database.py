"""
SQLite database layer for SDS results.

Provides upsert-per-document functionality so that partial results are
preserved even if a batch run fails midway.
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path
from typing import Optional

from sikkerhetsdatablad_agent.models import SDSData

logger = logging.getLogger(__name__)

# Default database path – can be overridden via .env or CLI
DEFAULT_DB_PATH = "sikkerhetsdatablad.db"

# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------

_CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS sds_results (
    source_url              TEXT PRIMARY KEY,
    product_name            TEXT,
    revision_date           TEXT,
    un_number               TEXT,
    proper_shipping_name    TEXT,
    transport_hazard_class  TEXT,
    packing_group           TEXT,
    environmental_hazards   TEXT,
    special_precautions_for_user TEXT,
    bulk_transport          TEXT,
    notes                   TEXT,
    created_at              TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at              TEXT NOT NULL DEFAULT (datetime('now'))
)
"""

_UPSERT_SQL = """
INSERT INTO sds_results (
    source_url,
    product_name,
    revision_date,
    un_number,
    proper_shipping_name,
    transport_hazard_class,
    packing_group,
    environmental_hazards,
    special_precautions_for_user,
    bulk_transport,
    notes,
    updated_at
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
ON CONFLICT(source_url) DO UPDATE SET
    product_name                = excluded.product_name,
    revision_date               = excluded.revision_date,
    un_number                   = excluded.un_number,
    proper_shipping_name        = excluded.proper_shipping_name,
    transport_hazard_class      = excluded.transport_hazard_class,
    packing_group               = excluded.packing_group,
    environmental_hazards       = excluded.environmental_hazards,
    special_precautions_for_user = excluded.special_precautions_for_user,
    bulk_transport              = excluded.bulk_transport,
    notes                       = excluded.notes,
    updated_at                  = excluded.updated_at
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_connection(db_path: str | Path) -> sqlite3.Connection:
    """Open (or create) the SQLite database and return a connection."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")  # safer concurrent access
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Ensure the sds_results table exists."""
    conn.execute(_CREATE_TABLE_SQL)
    conn.commit()
    logger.debug("Database initialised (table 'sds_results' ready).")


def upsert_result(conn: sqlite3.Connection, data: SDSData) -> None:
    """
    Insert or replace one SDSData row, keyed by source_url.

    Called immediately after each successful document parse so that
    partial progress is never lost.
    """
    flat = data.to_flat_dict()
    conn.execute(
        _UPSERT_SQL,
        (
            flat["source_url"],
            flat["product_name"],
            flat["revision_date"],
            flat["un_number"],
            flat["proper_shipping_name"],
            flat["transport_hazard_class"],
            flat["packing_group"],
            flat["environmental_hazards"],
            flat["special_precautions_for_user"],
            flat["bulk_transport"],
            flat["notes"],
        ),
    )
    conn.commit()
    logger.debug("Upserted result for %s", flat["source_url"])
