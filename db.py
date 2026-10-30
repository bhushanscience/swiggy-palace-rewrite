import aiosqlite
from datetime import datetime, timezone
from config import DATABASE_PATH

def now():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")

async def connect():
    db = await aiosqlite.connect(DATABASE_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA foreign_keys = ON")
    await db.execute("PRAGMA busy_timeout = 5000")
    return db

async def init_db():
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute("PRAGMA journal_mode = WAL")
        await db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS orders (
            id TEXT PRIMARY KEY,
            customer_id INTEGER NOT NULL REFERENCES users(telegram_id),
            status TEXT NOT NULL DEFAULT 'awaiting_address',
            address TEXT,
            cart_file_id TEXT,
            amount REAL,
            palace_charge REAL NOT NULL DEFAULT 0,
            total REAL,
            payment_utr TEXT,
            payment_status TEXT NOT NULL DEFAULT 'not_requested',
            swiggy_order_id TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id, created_at);
        CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status, created_at);
        CREATE TABLE IF NOT EXISTS seller_applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            full_name TEXT NOT NULL,
            details TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS support_tickets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            message TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            admin_reply TEXT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER NOT NULL,
            action TEXT NOT NULL,
            entity_id TEXT,
            created_at TEXT NOT NULL
        );
        """)
        await db.commit()

async def upsert_user(user):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            """INSERT INTO users(telegram_id, username, first_name, created_at)
               VALUES(?,?,?,?)
               ON CONFLICT(telegram_id) DO UPDATE SET
               username=excluded.username, first_name=excluded.first_name""",
            (user.id, user.username or "", user.first_name or "", now())
        )
        await db.commit()

async def create_order(user_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM orders WHERE customer_id=? AND status NOT IN ('completed','cancelled')",
            (user_id,)
        )
        count = (await cursor.fetchone())[0]
        if count:
            return None
        cursor = await db.execute(
            "SELECT COALESCE(MAX(CAST(SUBSTR(id,4) AS INTEGER)),999) + 1 FROM orders"
        )
        number = (await cursor.fetchone())[0]
        order_id = f"SP-{number}"
        stamp = now()
        await db.execute(
            "INSERT INTO orders(id,customer_id,status,created_at,updated_at) VALUES(?,?,?,?,?)",
            (order_id, user_id, "awaiting_address", stamp, stamp)
        )
        await db.commit()
        return order_id

async def get_order(order_id):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute("SELECT * FROM orders WHERE id=?", (order_id,))
        row = await cur.fetchone()
        return dict(row) if row else None

async def update_order(order_id, **fields):
    allowed = {
        "status", "address", "cart_file_id", "amount", "palace_charge",
        "total", "payment_utr", "payment_status", "swiggy_order_id"
    }
    if not fields or set(fields) - allowed:
        raise ValueError("Unsupported or empty order update")
    fields["updated_at"] = now()
    assignments = ", ".join(f"{key}=?" for key in fields)
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            f"UPDATE orders SET {assignments} WHERE id=?",
            (*fields.values(), order_id)
        )
        await db.commit()
        return cur.rowcount == 1

async def customer_orders(user_id, limit=10):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE customer_id=? ORDER BY created_at DESC LIMIT ?",
            (user_id, limit)
        )
        return [dict(row) for row in await cur.fetchall()]

async def pending_orders(limit=20):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        cur = await db.execute(
            "SELECT * FROM orders WHERE status NOT IN ('completed','cancelled') ORDER BY created_at LIMIT ?",
            (limit,)
        )
        return [dict(row) for row in await cur.fetchall()]

async def save_seller_application(user_id, full_name, details):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO seller_applications(user_id,full_name,details,created_at) VALUES(?,?,?,?)",
            (user_id, full_name[:120], details[:2000], now())
        )
        await db.commit()
        return cur.lastrowid

async def create_ticket(user_id, message):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute(
            "INSERT INTO support_tickets(user_id,message,created_at,updated_at) VALUES(?,?,?,?)",
            (user_id, message[:4000], now(), now())
        )
        await db.commit()
        return cur.lastrowid

async def get_setting(key, default=""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        cur = await db.execute("SELECT value FROM settings WHERE key=?", (key,))
        row = await cur.fetchone()
        return row[0] if row else default

async def set_setting(key, value):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO settings(key,value) VALUES(?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, str(value))
        )
        await db.commit()

async def audit(actor_id, action, entity_id=""):
    async with aiosqlite.connect(DATABASE_PATH) as db:
        await db.execute(
            "INSERT INTO audit_log(actor_id,action,entity_id,created_at) VALUES(?,?,?,?)",
            (actor_id, action[:200], str(entity_id)[:100], now())
        )
        await db.commit()
