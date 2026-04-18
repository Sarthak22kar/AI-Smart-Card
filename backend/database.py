"""
Database Layer  –  AI Smart Visiting Card System
=================================================
SQLite with:
  • Proper schema with all contact fields
  • Full-Text Search (FTS5) for fast keyword search
  • Fuzzy duplicate detection (name + phone + email)
  • Confidence scoring based on field completeness
  • Audit timestamps (created_at / updated_at)
  • Thread-safe connection-per-call pattern
  • Automatic schema migration (adds missing columns)
"""

import sqlite3
import json
import os
import re
from datetime import datetime
from typing import Optional

DB_PATH = os.path.join(os.path.dirname(__file__), "contacts.db")

# ── Schema ────────────────────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS contacts (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    name                  TEXT    NOT NULL DEFAULT '',
    phone                 TEXT    NOT NULL DEFAULT '',
    email                 TEXT    NOT NULL DEFAULT '',
    designation           TEXT    NOT NULL DEFAULT '',
    company               TEXT    NOT NULL DEFAULT '',
    address               TEXT    NOT NULL DEFAULT '',
    website               TEXT    NOT NULL DEFAULT '',
    gstin                 TEXT    NOT NULL DEFAULT '',
    raw_text              TEXT    NOT NULL DEFAULT '',
    extraction_confidence REAL    NOT NULL DEFAULT 0.0,
    ocr_engine            TEXT    NOT NULL DEFAULT '',
    image_formats         TEXT    NOT NULL DEFAULT '',
    validation_warnings   TEXT    NOT NULL DEFAULT '',
    created_at            TEXT    NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now','localtime'))
);
"""

# FTS5 virtual table for full-text search
_FTS_SCHEMA = """
CREATE VIRTUAL TABLE IF NOT EXISTS contacts_fts USING fts5(
    name, phone, email, designation, company, address,
    content='contacts',
    content_rowid='id'
);
"""

# Triggers to keep FTS in sync with the main table
_FTS_TRIGGERS = """
CREATE TRIGGER IF NOT EXISTS contacts_ai AFTER INSERT ON contacts BEGIN
    INSERT INTO contacts_fts(rowid, name, phone, email, designation, company, address)
    VALUES (new.id, new.name, new.phone, new.email, new.designation, new.company, new.address);
END;

CREATE TRIGGER IF NOT EXISTS contacts_ad AFTER DELETE ON contacts BEGIN
    INSERT INTO contacts_fts(contacts_fts, rowid, name, phone, email, designation, company, address)
    VALUES ('delete', old.id, old.name, old.phone, old.email, old.designation, old.company, old.address);
END;

CREATE TRIGGER IF NOT EXISTS contacts_au AFTER UPDATE ON contacts BEGIN
    INSERT INTO contacts_fts(contacts_fts, rowid, name, phone, email, designation, company, address)
    VALUES ('delete', old.id, old.name, old.phone, old.email, old.designation, old.company, old.address);
    INSERT INTO contacts_fts(rowid, name, phone, email, designation, company, address)
    VALUES (new.id, new.name, new.phone, new.email, new.designation, new.company, new.address);
END;
"""

_INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_name        ON contacts(name COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_phone       ON contacts(phone)",
    "CREATE INDEX IF NOT EXISTS idx_email       ON contacts(email COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_company     ON contacts(company COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_designation ON contacts(designation COLLATE NOCASE)",
    "CREATE INDEX IF NOT EXISTS idx_confidence  ON contacts(extraction_confidence DESC)",
    "CREATE INDEX IF NOT EXISTS idx_created     ON contacts(created_at DESC)",
]

# All columns that must exist (for migration)
_REQUIRED_COLUMNS = {
    'name':                  "TEXT NOT NULL DEFAULT ''",
    'phone':                 "TEXT NOT NULL DEFAULT ''",
    'email':                 "TEXT NOT NULL DEFAULT ''",
    'designation':           "TEXT NOT NULL DEFAULT ''",
    'company':               "TEXT NOT NULL DEFAULT ''",
    'address':               "TEXT NOT NULL DEFAULT ''",
    'website':               "TEXT NOT NULL DEFAULT ''",
    'gstin':                 "TEXT NOT NULL DEFAULT ''",
    'raw_text':              "TEXT NOT NULL DEFAULT ''",
    'extraction_confidence': "REAL NOT NULL DEFAULT 0.0",
    'ocr_engine':            "TEXT NOT NULL DEFAULT ''",
    'image_formats':         "TEXT NOT NULL DEFAULT ''",
    'validation_warnings':   "TEXT NOT NULL DEFAULT ''",
    'created_at':            "TEXT NOT NULL DEFAULT (datetime('now','localtime'))",
    'updated_at':            "TEXT NOT NULL DEFAULT (datetime('now','localtime'))",
}


# ── Connection ────────────────────────────────────────────────────────────────

def _conn() -> sqlite3.Connection:
    """Return a new connection with WAL mode and foreign keys enabled."""
    c = sqlite3.connect(DB_PATH, check_same_thread=False, timeout=10)
    c.execute("PRAGMA journal_mode=WAL")
    c.execute("PRAGMA foreign_keys=ON")
    c.execute("PRAGMA synchronous=NORMAL")
    c.row_factory = sqlite3.Row
    return c


# ── Confidence scoring ────────────────────────────────────────────────────────

# Weight of each field in the confidence score
_FIELD_WEIGHTS = {
    'name':        0.25,
    'phone':       0.20,
    'email':       0.20,
    'company':     0.15,
    'designation': 0.10,
    'address':     0.05,
    'website':     0.03,
    'gstin':       0.02,
}


def _compute_confidence(fields: dict) -> float:
    """
    Weighted confidence score (0.0 – 1.0).
    Each field contributes its weight only if it has a non-empty value.
    """
    score = 0.0
    for field, weight in _FIELD_WEIGHTS.items():
        val = fields.get(field, '')
        if val and str(val).strip() and str(val).strip().lower() not in ('unknown', 'n/a', '-'):
            score += weight
    return round(min(score, 1.0), 3)


# ── Normalisation helpers ─────────────────────────────────────────────────────

def _norm_phone(phone: str) -> str:
    """Strip all non-digit characters for duplicate comparison."""
    return re.sub(r'\D', '', phone or '')


def _norm_email(email: str) -> str:
    return (email or '').strip().lower()


def _norm_name(name: str) -> str:
    return re.sub(r'\s+', ' ', (name or '').strip().lower())


def _clean(val) -> str:
    """Ensure value is a clean string."""
    return str(val).strip() if val else ''


# ── Schema management ─────────────────────────────────────────────────────────

def create_table():
    """Create tables, indexes, FTS, and triggers. Migrate existing schema."""
    with _conn() as c:
        # Main table
        c.executescript(_SCHEMA)

        # Migration: add any missing columns
        existing = {row[1] for row in c.execute("PRAGMA table_info(contacts)")}
        for col, definition in _REQUIRED_COLUMNS.items():
            if col not in existing:
                c.execute(f"ALTER TABLE contacts ADD COLUMN {col} {definition}")
                print(f"  ➕ Added column: {col}")

        # Indexes
        for idx_sql in _INDEXES:
            c.execute(idx_sql)

        # FTS
        c.executescript(_FTS_SCHEMA)
        c.executescript(_FTS_TRIGGERS)

        # Backfill FTS for existing rows (safe to run multiple times)
        c.execute("""
            INSERT OR IGNORE INTO contacts_fts(rowid, name, phone, email, designation, company, address)
            SELECT id, name, phone, email, designation, company, address FROM contacts
        """)

    print("✅ Database schema ready")


# ── Write operations ──────────────────────────────────────────────────────────

def insert_contact(
    name: str,
    phone: str,
    email: str,
    designation: str,
    company: str,
    address: str,
    website: str = '',
    gstin: str = '',
    raw_text: str = '',
    image_formats: str = '',
    ocr_engine: str = '',
    validation_warnings: str = '',
) -> int:
    """
    Insert a new contact and return its ID.
    Confidence is computed automatically from field completeness.
    """
    fields = dict(
        name=_clean(name) or 'Unknown',
        phone=_clean(phone),
        email=_clean(email),
        designation=_clean(designation),
        company=_clean(company),
        address=_clean(address),
        website=_clean(website),
        gstin=_clean(gstin),
    )

    confidence = _compute_confidence(fields)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with _conn() as c:
        cur = c.execute("""
            INSERT INTO contacts
                (name, phone, email, designation, company, address,
                 website, gstin, raw_text, extraction_confidence,
                 ocr_engine, image_formats, validation_warnings,
                 created_at, updated_at)
            VALUES
                (:name, :phone, :email, :designation, :company, :address,
                 :website, :gstin, :raw_text, :confidence,
                 :ocr_engine, :image_formats, :validation_warnings,
                 :now, :now)
        """, {
            **fields,
            'raw_text':            raw_text[:1000],
            'confidence':          confidence,
            'ocr_engine':          _clean(ocr_engine),
            'image_formats':       _clean(image_formats),
            'validation_warnings': _clean(validation_warnings),
            'now':                 now,
        })
        contact_id = cur.lastrowid

    print(f"✅ Saved: ID={contact_id}  name='{fields['name']}'  "
          f"confidence={confidence:.0%}  engine={ocr_engine or 'unknown'}")
    return contact_id


def update_contact(contact_id: int, **kwargs) -> bool:
    """
    Update specific fields of an existing contact.
    Automatically recalculates confidence and updates updated_at.
    """
    if not kwargs:
        return False

    with _conn() as c:
        row = c.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
        if not row:
            return False

        # Merge existing values with updates
        current = dict(row)
        for k, v in kwargs.items():
            if k in current:
                current[k] = _clean(v)

        # Recompute confidence
        confidence = _compute_confidence(current)
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        set_clause = ', '.join(f"{k}=?" for k in kwargs)
        values = [_clean(v) for v in kwargs.values()]
        values += [confidence, now, contact_id]

        c.execute(
            f"UPDATE contacts SET {set_clause}, extraction_confidence=?, updated_at=? WHERE id=?",
            values
        )

    return True


def delete_contact(contact_id: int) -> bool:
    with _conn() as c:
        c.execute("DELETE FROM contacts WHERE id=?", (contact_id,))
    return True


# ── Read operations ───────────────────────────────────────────────────────────

def get_all_contacts() -> list:
    """Return all contacts ordered by creation date (newest first)."""
    with _conn() as c:
        rows = c.execute("""
            SELECT id, name, phone, email, designation, company, address,
                   website, gstin, extraction_confidence, created_at
            FROM contacts
            ORDER BY created_at DESC
        """).fetchall()
    return [tuple(r) for r in rows]


def get_contact_by_id(contact_id: int) -> Optional[tuple]:
    with _conn() as c:
        row = c.execute("SELECT * FROM contacts WHERE id=?", (contact_id,)).fetchone()
    return tuple(row) if row else None


def get_contact_stats() -> dict:
    """Return aggregate statistics about the contacts database."""
    with _conn() as c:
        total = c.execute("SELECT COUNT(*) FROM contacts").fetchone()[0]

        avg_conf = c.execute(
            "SELECT AVG(extraction_confidence) FROM contacts"
        ).fetchone()[0] or 0.0

        by_designation = dict(c.execute("""
            SELECT designation, COUNT(*) as cnt
            FROM contacts
            WHERE designation != '' AND designation IS NOT NULL
            GROUP BY designation
            ORDER BY cnt DESC
            LIMIT 20
        """).fetchall())

        by_company = dict(c.execute("""
            SELECT company, COUNT(*) as cnt
            FROM contacts
            WHERE company != '' AND company IS NOT NULL
            GROUP BY company
            ORDER BY cnt DESC
            LIMIT 10
        """).fetchall())

        by_engine = dict(c.execute("""
            SELECT ocr_engine, COUNT(*) as cnt
            FROM contacts
            WHERE ocr_engine != ''
            GROUP BY ocr_engine
            ORDER BY cnt DESC
        """).fetchall())

        high_conf = c.execute(
            "SELECT COUNT(*) FROM contacts WHERE extraction_confidence >= 0.7"
        ).fetchone()[0]

        low_conf = c.execute(
            "SELECT COUNT(*) FROM contacts WHERE extraction_confidence < 0.4"
        ).fetchone()[0]

        recent = c.execute("""
            SELECT id, name, company, extraction_confidence, created_at
            FROM contacts
            ORDER BY created_at DESC
            LIMIT 5
        """).fetchall()

    return {
        "total_contacts":      total,
        "average_confidence":  round(avg_conf, 3),
        "high_confidence":     high_conf,
        "low_confidence":      low_conf,
        "by_designation":      by_designation,
        "by_company":          by_company,
        "by_ocr_engine":       by_engine,
        "recent_contacts":     [dict(r) for r in recent],
    }


# ── Duplicate detection ───────────────────────────────────────────────────────

def find_duplicate(
    name: str,
    phone: str,
    email: str,
) -> Optional[tuple]:
    """
    Fuzzy duplicate detection:
      - Exact email match (case-insensitive)
      - Exact phone match (digits only)
      - Exact name match (case-insensitive, normalised whitespace)

    Returns the first matching row or None.
    """
    norm_phone = _norm_phone(phone)
    norm_email = _norm_email(email)
    norm_name  = _norm_name(name)

    with _conn() as c:
        # 1. Email match (most reliable)
        if norm_email:
            row = c.execute("""
                SELECT * FROM contacts
                WHERE email != '' AND LOWER(TRIM(email)) = ?
                LIMIT 1
            """, (norm_email,)).fetchone()
            if row:
                return tuple(row)

        # 2. Phone match (digits only)
        if norm_phone and len(norm_phone) >= 10:
            # Compare last 10 digits to handle country code variations
            last10 = norm_phone[-10:]
            rows = c.execute("""
                SELECT * FROM contacts
                WHERE phone != ''
                LIMIT 200
            """).fetchall()
            for row in rows:
                if _norm_phone(row['phone'])[-10:] == last10:
                    return tuple(row)

        # 3. Name match (case-insensitive, skip generic names)
        if norm_name and norm_name not in ('unknown', 'unknown contact', ''):
            row = c.execute("""
                SELECT * FROM contacts
                WHERE name != ''
                  AND name NOT IN ('Unknown', 'Unknown Contact')
                  AND LOWER(TRIM(REPLACE(name, '  ', ' '))) = ?
                LIMIT 1
            """, (norm_name,)).fetchone()
            if row:
                return tuple(row)

    return None


# ── Search ────────────────────────────────────────────────────────────────────

def search_contacts_advanced(query: str) -> list:
    """
    Full-text search using FTS5 with fallback to LIKE search.
    Returns contacts ordered by relevance (FTS rank) then confidence.
    """
    if not query or not query.strip():
        return get_all_contacts()

    q = query.strip()

    with _conn() as c:
        # Try FTS5 first
        try:
            rows = c.execute("""
                SELECT c.id, c.name, c.phone, c.email, c.designation,
                       c.company, c.address, c.website, c.gstin,
                       c.extraction_confidence, c.created_at
                FROM contacts c
                JOIN contacts_fts f ON c.id = f.rowid
                WHERE contacts_fts MATCH ?
                ORDER BY rank, c.extraction_confidence DESC
                LIMIT 50
            """, (q,)).fetchall()
            if rows:
                return [tuple(r) for r in rows]
        except Exception:
            pass

        # Fallback: LIKE search across key fields
        like = f"%{q}%"
        rows = c.execute("""
            SELECT id, name, phone, email, designation, company, address,
                   website, gstin, extraction_confidence, created_at
            FROM contacts
            WHERE name        LIKE ? COLLATE NOCASE
               OR phone       LIKE ?
               OR email       LIKE ? COLLATE NOCASE
               OR designation LIKE ? COLLATE NOCASE
               OR company     LIKE ? COLLATE NOCASE
               OR address     LIKE ? COLLATE NOCASE
            ORDER BY extraction_confidence DESC
            LIMIT 50
        """, (like, like, like, like, like, like)).fetchall()

    return [tuple(r) for r in rows]


def get_contacts_by_profession(profession: str) -> list:
    with _conn() as c:
        rows = c.execute("""
            SELECT id, name, phone, email, designation, company, address,
                   website, gstin, extraction_confidence, created_at
            FROM contacts
            WHERE designation LIKE ? COLLATE NOCASE
            ORDER BY extraction_confidence DESC, created_at DESC
        """, (f"%{profession}%",)).fetchall()
    return [tuple(r) for r in rows]


def get_low_confidence_contacts(threshold: float = 0.4) -> list:
    with _conn() as c:
        rows = c.execute("""
            SELECT id, name, phone, email, designation, company,
                   extraction_confidence, created_at
            FROM contacts
            WHERE extraction_confidence < ?
            ORDER BY extraction_confidence ASC
        """, (threshold,)).fetchall()
    return [tuple(r) for r in rows]


# ── Backup / restore ──────────────────────────────────────────────────────────

def backup_contacts_to_json(filename: str = "contacts_backup.json") -> int:
    with _conn() as c:
        rows = c.execute("SELECT * FROM contacts").fetchall()
        cols = [d[0] for d in c.execute("SELECT * FROM contacts LIMIT 0").description or []]
        if not cols:
            cols = list(_REQUIRED_COLUMNS.keys())

    data = [dict(zip(cols, tuple(r))) for r in rows]
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, default=str, ensure_ascii=False)
    print(f"✅ Backed up {len(data)} contacts to {filename}")
    return len(data)


# ── Init ──────────────────────────────────────────────────────────────────────

def init_database():
    create_table()
    print("✅ Database ready")


if __name__ == "__main__":
    init_database()
    stats = get_contact_stats()
    print(json.dumps(stats, indent=2, default=str))
