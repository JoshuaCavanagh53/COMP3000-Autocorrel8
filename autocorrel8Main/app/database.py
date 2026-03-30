import sqlite3
import os
import json


DB_PATH = os.path.join(os.path.expanduser("~"), ".autocorrel8", "autocorrel8.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def get_connection() -> sqlite3.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row          # access columns by name
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def _migrate_db():
    # Adds columns introduced after the initial schema without dropping existing data
    migrations = [
        "ALTER TABLE bookmarks ADD COLUMN notes TEXT DEFAULT ''",
    ]
    # New tables that may not exist on older databases
    table_migrations = [
        """CREATE TABLE IF NOT EXISTS registry_bookmarks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL REFERENCES cases(id),
            key_path TEXT NOT NULL,
            value_name TEXT NOT NULL,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT (datetime('now')),
            UNIQUE(case_id, key_path, value_name)
        )"""
    ]
    with get_connection() as conn:
        for sql in migrations:
            try:
                conn.execute(sql)
            except sqlite3.OperationalError:
                pass
        for sql in table_migrations:
            conn.executescript(sql)


def init_db():
    # Read schema from file and execute it
    with open(SCHEMA_PATH, "r") as f:
        schema = f.read()
    with get_connection() as conn:
        conn.executescript(schema)
    _migrate_db()


# Cases 

def create_case(name: str, path: str, investigator: str = None) -> int:
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT OR IGNORE INTO cases (name, path, investigator) VALUES (?, ?, ?)",
            (name, path, investigator)
        )
        if cur.lastrowid:
            return cur.lastrowid
        # Already exists — return existing id
        row = conn.execute(
            "SELECT id FROM cases WHERE path = ?", (path,)
        ).fetchone()
        return row['id']


def get_case(case_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM cases WHERE id = ?", (case_id,)
        ).fetchone()
        return dict(row) if row else None


def get_all_cases() -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM cases ORDER BY created_at DESC"
        ).fetchall()
        return [dict(r) for r in rows]


def update_case_notes(case_id: int, notes: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE cases SET notes = ? WHERE id = ?", (notes, case_id)
        )


# Packets

def save_packets(case_id: int, filename: str, data: list):
    # Insert or replace packet data for a given file in this case
    with get_connection() as conn:
        conn.execute(
            """INSERT INTO packets (case_id, filename, data)
               VALUES (?, ?, ?)
               ON CONFLICT(case_id, filename) DO UPDATE SET data = excluded.data""",
            (case_id, filename, json.dumps(data))
        )


def get_packets(case_id: int, filename: str) -> list:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT data FROM packets WHERE case_id = ? AND filename = ?",
            (case_id, filename)
        ).fetchone()
        return json.loads(row['data']) if row else []


def get_packet_filenames(case_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT filename FROM packets WHERE case_id = ?", (case_id,)
        ).fetchall()
        return [r['filename'] for r in rows]


def delete_packets(case_id: int, filename: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM packets WHERE case_id = ? AND filename = ?",
            (case_id, filename)
        )


# Runs

def save_run(case_id: int, pcap_files: list, gaps: list) -> int:
    # Save a correlation run and all its gap results, returns the new run id
    with get_connection() as conn:
        cur = conn.execute(
            "INSERT INTO runs (case_id, pcap_files, gap_count) VALUES (?, ?, ?)",
            (case_id, json.dumps(pcap_files), len(gaps))
        )
        run_id = cur.lastrowid
        conn.executemany(
            """INSERT INTO gaps
               (run_id, domain, category, count, first_seen, last_seen, duration)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            [(run_id,
              g['domain'],
              g['category'],
              g['count'],
              g['first_seen'].isoformat(),
              g['last_seen'].isoformat(),
              str(g.get('duration', '')))
             for g in gaps]
        )
        return run_id


def get_runs_for_case(case_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM runs WHERE case_id = ? ORDER BY run_at DESC",
            (case_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_latest_run(case_id: int) -> dict:
    with get_connection() as conn:
        row = conn.execute(
            "SELECT * FROM runs WHERE case_id = ? ORDER BY run_at DESC LIMIT 1",
            (case_id,)
        ).fetchone()
        return dict(row) if row else None


# Gaps

def get_gaps_for_run(run_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM gaps WHERE run_id = ?", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    
def get_bookmarked_gaps(run_id: int) -> list:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT * FROM gaps WHERE run_id = ? AND bookmarked = 1", (run_id,)
        ).fetchall()
        return [dict(r) for r in rows]
    

# Bookmarks


def add_bookmark(case_id: int, domain: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO bookmarks (case_id, domain) VALUES (?, ?)",
            (case_id, domain)
        )


def remove_bookmark(case_id: int, domain: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM bookmarks WHERE case_id = ? AND domain = ?",
            (case_id, domain)
        )


def get_bookmarks_for_case(case_id: int) -> dict:
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT domain, notes FROM bookmarks WHERE case_id = ?", (case_id,)
        ).fetchall()
        return {r['domain']: (r['notes'] or '') for r in rows}
    

def update_bookmark_note(case_id: int, domain: str, note: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE bookmarks SET notes = ? WHERE case_id = ? AND domain = ?",
            (note, case_id, domain)
        )


def toggle_bookmark(case_id: int, domain: str, bookmarked: bool):
    if bookmarked:
        add_bookmark(case_id, domain)
    else:
        remove_bookmark(case_id, domain)


# Registry bookmarks
def add_registry_bookmark(case_id: int, key_path: str, value_name: str):
    with get_connection() as conn:
        conn.execute(
            "INSERT OR IGNORE INTO registry_bookmarks (case_id, key_path, value_name, notes) VALUES (?, ?, ?, '')",
            (case_id, key_path, value_name)
        )
 
 
def remove_registry_bookmark(case_id: int, key_path: str, value_name: str):
    with get_connection() as conn:
        conn.execute(
            "DELETE FROM registry_bookmarks WHERE case_id = ? AND key_path = ? AND value_name = ?",
            (case_id, key_path, value_name)
        )
 
 
def get_registry_bookmarks_for_case(case_id: int) -> dict:
    # Returns {(key_path, value_name): notes}
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT key_path, value_name, notes FROM registry_bookmarks WHERE case_id = ?",
            (case_id,)
        ).fetchall()
        return {(r['key_path'], r['value_name']): (r['notes'] or '') for r in rows}
 
 
def update_registry_bookmark_note(case_id: int, key_path: str, value_name: str, note: str):
    with get_connection() as conn:
        conn.execute(
            "UPDATE registry_bookmarks SET notes = ? WHERE case_id = ? AND key_path = ? AND value_name = ?",
            (note, case_id, key_path, value_name)
        )
 
 
def toggle_registry_bookmark(case_id: int, key_path: str, value_name: str, bookmarked: bool):
    if bookmarked:
        add_registry_bookmark(case_id, key_path, value_name)
    else:
        remove_registry_bookmark(case_id, key_path, value_name)