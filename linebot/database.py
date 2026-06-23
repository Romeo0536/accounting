import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), 'mochi.db')


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS group_settings (
        group_id TEXT PRIMARY KEY,
        group_name TEXT DEFAULT '',
        email TEXT DEFAULT '',
        notifications_enabled INTEGER DEFAULT 1,
        archiving_enabled INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS scheduled_messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id TEXT NOT NULL,
        message TEXT NOT NULL,
        scheduled_time TIMESTAMP NOT NULL,
        is_sent INTEGER DEFAULT 0,
        created_by TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS admins (
        user_id TEXT PRIMARY KEY,
        display_name TEXT DEFAULT '',
        added_by TEXT DEFAULT '',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS archive_stats (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        group_id TEXT NOT NULL,
        date TEXT NOT NULL,
        images_count INTEGER DEFAULT 0,
        videos_count INTEGER DEFAULT 0,
        files_count INTEGER DEFAULT 0,
        messages_count INTEGER DEFAULT 0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(group_id, date)
    )''')

    conn.commit()
    conn.close()


# ─── Group Settings ────────────────────────────────────────────────────────────

def get_group_settings(group_id: str) -> dict:
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM group_settings WHERE group_id = ?', (group_id,)
    ).fetchone()
    conn.close()
    if row:
        return dict(row)
    return {
        'group_id': group_id,
        'group_name': '',
        'email': '',
        'notifications_enabled': 1,
        'archiving_enabled': 1,
    }


def upsert_group_settings(group_id: str, **kwargs):
    conn = get_db()
    existing = conn.execute(
        'SELECT group_id FROM group_settings WHERE group_id = ?', (group_id,)
    ).fetchone()

    if existing:
        set_clause = ', '.join(f'{k} = ?' for k in kwargs)
        values = list(kwargs.values()) + [group_id]
        conn.execute(
            f'UPDATE group_settings SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE group_id = ?',
            values
        )
    else:
        kwargs['group_id'] = group_id
        cols = ', '.join(kwargs.keys())
        placeholders = ', '.join('?' * len(kwargs))
        conn.execute(
            f'INSERT INTO group_settings ({cols}) VALUES ({placeholders})',
            list(kwargs.values())
        )
    conn.commit()
    conn.close()


# ─── Scheduled Messages ────────────────────────────────────────────────────────

def add_scheduled_message(group_id: str, message: str, scheduled_time, created_by: str = '') -> int:
    conn = get_db()
    cursor = conn.execute(
        'INSERT INTO scheduled_messages (group_id, message, scheduled_time, created_by) VALUES (?, ?, ?, ?)',
        (group_id, message, scheduled_time, created_by)
    )
    msg_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return msg_id


def get_pending_scheduled_messages():
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scheduled_messages WHERE is_sent = 0 AND scheduled_time <= datetime('now') ORDER BY scheduled_time ASC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_upcoming_scheduled_messages(group_id: str):
    conn = get_db()
    rows = conn.execute(
        "SELECT * FROM scheduled_messages WHERE group_id = ? AND is_sent = 0 AND scheduled_time > datetime('now') ORDER BY scheduled_time ASC LIMIT 10",
        (group_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def mark_message_sent(msg_id: int):
    conn = get_db()
    conn.execute('UPDATE scheduled_messages SET is_sent = 1 WHERE id = ?', (msg_id,))
    conn.commit()
    conn.close()


def delete_scheduled_message(msg_id: int, group_id: str) -> bool:
    conn = get_db()
    cursor = conn.execute(
        'DELETE FROM scheduled_messages WHERE id = ? AND group_id = ? AND is_sent = 0',
        (msg_id, group_id)
    )
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    return deleted


# ─── Admins ────────────────────────────────────────────────────────────────────

def is_admin(user_id: str) -> bool:
    env_admins = os.environ.get('ADMIN_USER_IDS', '').split(',')
    if user_id in [a.strip() for a in env_admins if a.strip()]:
        return True
    conn = get_db()
    row = conn.execute('SELECT user_id FROM admins WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return row is not None


def add_admin(user_id: str, display_name: str = '', added_by: str = ''):
    conn = get_db()
    conn.execute(
        'INSERT OR IGNORE INTO admins (user_id, display_name, added_by) VALUES (?, ?, ?)',
        (user_id, display_name, added_by)
    )
    conn.commit()
    conn.close()


def remove_admin(user_id: str):
    conn = get_db()
    conn.execute('DELETE FROM admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()


# ─── Archive Stats ─────────────────────────────────────────────────────────────

def increment_stat(group_id: str, date: str, field: str):
    conn = get_db()
    conn.execute(
        f'''INSERT INTO archive_stats (group_id, date, {field})
            VALUES (?, ?, 1)
            ON CONFLICT(group_id, date)
            DO UPDATE SET {field} = {field} + 1, updated_at = CURRENT_TIMESTAMP''',
        (group_id, date)
    )
    conn.commit()
    conn.close()


def get_stats(group_id: str, days: int = 7) -> list:
    conn = get_db()
    rows = conn.execute(
        f"""SELECT * FROM archive_stats
            WHERE group_id = ? AND date >= date('now', '-{days} days')
            ORDER BY date DESC""",
        (group_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
