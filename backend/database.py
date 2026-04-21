"""
Database Layer  –  AI Smart Visiting Card System
=================================================
MySQL database with:
  • Full contact schema
  • Fuzzy duplicate detection (name + phone + email)
  • Confidence scoring based on field completeness
  • Audit timestamps (created_at / updated_at)
  • Thread-safe connection pool
"""

import json
import os
import re
from datetime import datetime
from typing import Optional

import mysql.connector
from mysql.connector import pooling

# ── Load config from .env ─────────────────────────────────────────────────────

def _load_env():
    cfg = {
        'host':     os.environ.get('MYSQL_HOST',     'localhost'),
        'port':     int(os.environ.get('MYSQL_PORT', '3306')),
        'database': os.environ.get('MYSQL_DATABASE', 'ai_smart_card'),
        'user':     os.environ.get('MYSQL_USER',     'root'),
        'password': os.environ.get('MYSQL_PASSWORD', ''),
    }
    # Also read directly from .env file if env vars not set
    env_file = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_file):
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line.startswith('MYSQL_HOST='):
                    cfg['host'] = line.split('=', 1)[1].strip()
                elif line.startswith('MYSQL_PORT='):
                    cfg['port'] = int(line.split('=', 1)[1].strip())
                elif line.startswith('MYSQL_DATABASE='):
                    cfg['database'] = line.split('=', 1)[1].strip()
                elif line.startswith('MYSQL_USER='):
                    cfg['user'] = line.split('=', 1)[1].strip()
                elif line.startswith('MYSQL_PASSWORD='):
                    cfg['password'] = line.split('=', 1)[1].strip()
    return cfg

_DB_CONFIG = _load_env()

# ── Connection pool ───────────────────────────────────────────────────────────

_pool = None

def _get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name    = "ai_card_pool",
            pool_size    = 5,
            pool_reset_session = True,
            host         = _DB_CONFIG['host'],
            port         = _DB_CONFIG['port'],
            database     = _DB_CONFIG['database'],
            user         = _DB_CONFIG['user'],
            password     = _DB_CONFIG['password'],
            charset      = 'utf8mb4',
            collation    = 'utf8mb4_unicode_ci',
            autocommit   = False,
        )
    return _pool


def _conn():
    """Get a connection from the pool."""
    return _get_pool().get_connection()


# ── Confidence scoring ────────────────────────────────────────────────────────

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
    score = 0.0
    for field, weight in _FIELD_WEIGHTS.items():
        val = fields.get(field, '')
        if val and str(val).strip() and str(val).strip().lower() not in ('unknown', 'n/a', '-'):
            score += weight
    return round(min(score, 1.0), 3)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _norm_phone(phone: str) -> str:
    return re.sub(r'\D', '', phone or '')

def _norm_email(email: str) -> str:
    return (email or '').strip().lower()

def _norm_name(name: str) -> str:
    return re.sub(r'\s+', ' ', (name or '').strip().lower())

def _clean(val) -> str:
    return str(val).strip() if val else ''


# ── Schema management ─────────────────────────────────────────────────────────

def create_table():
    """Verify table exists and is accessible."""
    try:
        con = _conn()
        cur = con.cursor()
        cur.execute("SELECT COUNT(*) FROM contacts")
        count = cur.fetchone()[0]
        cur.close()
        con.close()
        print(f"✅ MySQL connected — contacts table has {count} rows")
    except mysql.connector.Error as e:
        print(f"❌ MySQL connection failed: {e}")
        print(f"   Host: {_DB_CONFIG['host']}:{_DB_CONFIG['port']}")
        print(f"   DB:   {_DB_CONFIG['database']}")
        print(f"   User: {_DB_CONFIG['user']}")
        raise


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
    services: str = '',
    raw_text: str = '',
    image_formats: str = '',
    ocr_engine: str = '',
    validation_warnings: str = '',
) -> int:
    fields = dict(
        name        = _clean(name) or 'Unknown',
        phone       = _clean(phone),
        email       = _clean(email),
        designation = _clean(designation),
        company     = _clean(company),
        address     = _clean(address),
        website     = _clean(website),
        gstin       = _clean(gstin),
    )
    confidence = _compute_confidence(fields)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    sql = """
        INSERT INTO contacts
            (name, phone, email, designation, company, address,
             website, gstin, services, raw_text, extraction_confidence,
             ocr_engine, image_formats, validation_warnings,
             created_at, updated_at)
        VALUES
            (%s, %s, %s, %s, %s, %s,
             %s, %s, %s, %s, %s,
             %s, %s, %s,
             %s, %s)
    """
    values = (
        fields['name'], fields['phone'], fields['email'],
        fields['designation'], fields['company'], fields['address'],
        fields['website'], fields['gstin'], _clean(services)[:500],
        raw_text[:1000], confidence,
        _clean(ocr_engine), _clean(image_formats), _clean(validation_warnings),
        now, now,
    )

    con = _conn()
    cur = con.cursor()
    cur.execute(sql, values)
    contact_id = cur.lastrowid
    con.commit()
    cur.close()
    con.close()

    print(f"✅ Saved: ID={contact_id}  name='{fields['name']}'  "
          f"confidence={confidence:.0%}  engine={ocr_engine or 'unknown'}")
    return contact_id


def update_contact(contact_id: int, **kwargs) -> bool:
    if not kwargs:
        return False

    allowed = {'name', 'phone', 'email', 'designation', 'company',
               'address', 'website', 'gstin', 'services'}
    updates = {k: _clean(v) for k, v in kwargs.items() if k in allowed}
    if not updates:
        return False

    # Recompute confidence with updated values
    con = _conn()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    row = cur.fetchone()
    if not row:
        cur.close(); con.close()
        return False

    current = dict(row)
    current.update(updates)
    confidence = _compute_confidence(current)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    set_parts = ', '.join(f"`{k}` = %s" for k in updates)
    values    = list(updates.values()) + [confidence, now, contact_id]

    cur.execute(
        f"UPDATE contacts SET {set_parts}, extraction_confidence = %s, updated_at = %s WHERE id = %s",
        values
    )
    con.commit()
    cur.close()
    con.close()
    return True


def delete_contact(contact_id: int) -> bool:
    con = _conn()
    cur = con.cursor()
    cur.execute("DELETE FROM contacts WHERE id = %s", (contact_id,))
    con.commit()
    cur.close()
    con.close()
    return True


# ── Read operations ───────────────────────────────────────────────────────────

def get_all_contacts() -> list:
    con = _conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, phone, email, designation, company, address,
               website, gstin, services, extraction_confidence, created_at
        FROM contacts
        ORDER BY created_at DESC
    """)
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows


def get_contact_by_id(contact_id: int) -> Optional[tuple]:
    con = _conn()
    cur = con.cursor()
    cur.execute("SELECT * FROM contacts WHERE id = %s", (contact_id,))
    row = cur.fetchone()
    cur.close(); con.close()
    return row


def get_contact_stats() -> dict:
    con = _conn()
    cur = con.cursor()

    cur.execute("SELECT COUNT(*) FROM contacts")
    total = cur.fetchone()[0]

    cur.execute("SELECT AVG(extraction_confidence) FROM contacts")
    avg_conf = cur.fetchone()[0] or 0.0

    cur.execute("""
        SELECT designation, COUNT(*) as cnt FROM contacts
        WHERE designation != '' AND designation IS NOT NULL
        GROUP BY designation ORDER BY cnt DESC LIMIT 20
    """)
    by_designation = dict(cur.fetchall())

    cur.execute("""
        SELECT company, COUNT(*) as cnt FROM contacts
        WHERE company != '' AND company IS NOT NULL
        GROUP BY company ORDER BY cnt DESC LIMIT 10
    """)
    by_company = dict(cur.fetchall())

    cur.execute("""
        SELECT ocr_engine, COUNT(*) as cnt FROM contacts
        WHERE ocr_engine != '' GROUP BY ocr_engine ORDER BY cnt DESC
    """)
    by_engine = dict(cur.fetchall())

    cur.execute("SELECT COUNT(*) FROM contacts WHERE extraction_confidence >= 0.7")
    high_conf = cur.fetchone()[0]

    cur.execute("SELECT COUNT(*) FROM contacts WHERE extraction_confidence < 0.4")
    low_conf = cur.fetchone()[0]

    cur.execute("""
        SELECT id, name, company, extraction_confidence, created_at
        FROM contacts ORDER BY created_at DESC LIMIT 5
    """)
    recent = [
        {"id": r[0], "name": r[1], "company": r[2],
         "extraction_confidence": r[3], "created_at": str(r[4])}
        for r in cur.fetchall()
    ]

    cur.close(); con.close()
    return {
        "total_contacts":     total,
        "average_confidence": round(float(avg_conf), 3),
        "high_confidence":    high_conf,
        "low_confidence":     low_conf,
        "by_designation":     by_designation,
        "by_company":         by_company,
        "by_ocr_engine":      by_engine,
        "recent_contacts":    recent,
    }


# ── Duplicate detection ───────────────────────────────────────────────────────

def find_duplicate(name: str, phone: str, email: str) -> Optional[tuple]:
    norm_phone = _norm_phone(phone)
    norm_email = _norm_email(email)
    norm_name  = _norm_name(name)

    con = _conn()
    cur = con.cursor()

    # 1. Email match
    if norm_email:
        cur.execute(
            "SELECT * FROM contacts WHERE email != '' AND LOWER(TRIM(email)) = %s LIMIT 1",
            (norm_email,)
        )
        row = cur.fetchone()
        if row:
            cur.close(); con.close()
            return row

    # 2. Phone match (last 10 digits)
    if norm_phone and len(norm_phone) >= 10:
        last10 = norm_phone[-10:]
        cur.execute("SELECT * FROM contacts WHERE phone != '' LIMIT 500")
        for row in cur.fetchall():
            if _norm_phone(str(row[2]))[-10:] == last10:
                cur.close(); con.close()
                return row

    # 3. Name match
    if norm_name and norm_name not in ('unknown', 'unknown contact', ''):
        cur.execute("""
            SELECT * FROM contacts
            WHERE name != '' AND name NOT IN ('Unknown', 'Unknown Contact')
            AND LOWER(TRIM(name)) = %s LIMIT 1
        """, (norm_name,))
        row = cur.fetchone()
        if row:
            cur.close(); con.close()
            return row

    cur.close(); con.close()
    return None


# ── Search ────────────────────────────────────────────────────────────────────

def search_contacts_advanced(query: str) -> list:
    if not query or not query.strip():
        return get_all_contacts()

    like = f"%{query.strip()}%"
    con = _conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, phone, email, designation, company, address,
               website, gstin, services, extraction_confidence, created_at
        FROM contacts
        WHERE name        LIKE %s
           OR phone       LIKE %s
           OR email       LIKE %s
           OR designation LIKE %s
           OR company     LIKE %s
           OR address     LIKE %s
           OR services    LIKE %s
        ORDER BY extraction_confidence DESC
        LIMIT 50
    """, (like, like, like, like, like, like, like))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows


def get_contacts_by_profession(profession: str) -> list:
    con = _conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, phone, email, designation, company, address,
               website, gstin, extraction_confidence, created_at
        FROM contacts WHERE designation LIKE %s
        ORDER BY extraction_confidence DESC, created_at DESC
    """, (f"%{profession}%",))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows


def get_low_confidence_contacts(threshold: float = 0.4) -> list:
    con = _conn()
    cur = con.cursor()
    cur.execute("""
        SELECT id, name, phone, email, designation, company,
               extraction_confidence, created_at
        FROM contacts WHERE extraction_confidence < %s
        ORDER BY extraction_confidence ASC
    """, (threshold,))
    rows = cur.fetchall()
    cur.close(); con.close()
    return rows


def backup_contacts_to_json(filename: str = "contacts_backup.json") -> int:
    con = _conn()
    cur = con.cursor(dictionary=True)
    cur.execute("SELECT * FROM contacts")
    data = cur.fetchall()
    cur.close(); con.close()
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
