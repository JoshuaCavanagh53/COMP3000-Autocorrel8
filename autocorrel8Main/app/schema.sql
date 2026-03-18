-- AutoCorrel8 database schema

CREATE TABLE IF NOT EXISTS cases (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    name         TEXT NOT NULL,
    path         TEXT NOT NULL UNIQUE,
    investigator TEXT,
    created_at   TEXT DEFAULT (datetime('now')),
    notes        TEXT
);

CREATE TABLE IF NOT EXISTS packets (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id     INTEGER NOT NULL REFERENCES cases(id),
    filename    TEXT NOT NULL,
    data        TEXT NOT NULL,              -- JSON blob of parsed packet data
    uploaded_at TEXT DEFAULT (datetime('now')),
    UNIQUE(case_id, filename)
);

CREATE TABLE IF NOT EXISTS runs (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL REFERENCES cases(id),
    run_at     TEXT DEFAULT (datetime('now')),
    pcap_files TEXT,                        -- JSON list of filenames used
    gap_count  INTEGER
);

CREATE TABLE IF NOT EXISTS gaps (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id     INTEGER NOT NULL REFERENCES runs(id),
    domain     TEXT NOT NULL,
    category   TEXT,
    count      INTEGER,
    first_seen TEXT,
    last_seen  TEXT,
    duration   TEXT,
    bookmarked INTEGER DEFAULT 0            -- 0 or 1
);

CREATE TABLE IF NOT EXISTS bookmarks (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    case_id    INTEGER NOT NULL REFERENCES cases(id),
    domain     TEXT NOT NULL,
    notes      TEXT DEFAULT '',
    created_at TEXT DEFAULT (datetime('now')),
    UNIQUE(case_id, domain)
);