#!/usr/bin/env python3
"""
================================================================================
POST DATABASE INITIALIZER (init_post_db.py)
================================================================================
Author: Digital Misfit / Captain Misfit (Ryan Caron)
Engine: AntiGravity (AGY) Cognitive Architecture / POST Protocol

Provisions dedicated SQLite database at DataStorage/POST/database/post_telemetry.sqlite
================================================================================
"""

import sqlite3
from pathlib import Path

POST_DIR = Path(__file__).parent.parent.resolve()
DB_PATH = POST_DIR / "database" / "post_telemetry.sqlite"
SCHEMA_PATH = POST_DIR / "database" / "schema.sql"


def init_db():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    with open(SCHEMA_PATH, "r") as f:
        schema_sql = f.read()
        
    cursor.executescript(schema_sql)
    conn.commit()
    conn.close()
    print(f"[✓] POST Telemetry Database initialized at: {DB_PATH}")


if __name__ == "__main__":
    init_db()
