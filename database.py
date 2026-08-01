import sqlite3
from pathlib import Path
from typing import Optional

DB_PATH = Path(__file__).with_name("fitzery.db")


def connect():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _column_names(conn, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row["name"] for row in rows}


def initialize_database():
    conn = connect()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            plan TEXT DEFAULT 'Starter',
            plan_status TEXT DEFAULT 'test',
            stripe_customer_id TEXT DEFAULT '',
            stripe_subscription_id TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    user_columns = _column_names(conn, "users")
    migrations = {
        "plan": "ALTER TABLE users ADD COLUMN plan TEXT DEFAULT 'Starter'",
        "plan_status": "ALTER TABLE users ADD COLUMN plan_status TEXT DEFAULT 'test'",
        "stripe_customer_id": "ALTER TABLE users ADD COLUMN stripe_customer_id TEXT DEFAULT ''",
        "stripe_subscription_id": "ALTER TABLE users ADD COLUMN stripe_subscription_id TEXT DEFAULT ''",
    }

    for column, statement in migrations.items():
        if column not in user_columns:
            cur.execute(statement)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS business_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            business_name TEXT DEFAULT 'My Business',
            industry TEXT DEFAULT 'General Business',
            location TEXT DEFAULT '',
            services TEXT DEFAULT '',
            ideal_customer TEXT DEFAULT '',
            brand_voice TEXT DEFAULT 'Professional, friendly, and trustworthy',
            monthly_revenue REAL DEFAULT 0,
            monthly_goal REAL DEFAULT 10000,
            marketing_budget REAL DEFAULT 1000,
            employees INTEGER DEFAULT 1,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            email TEXT DEFAULT '',
            phone TEXT DEFAULT '',
            company TEXT DEFAULT '',
            status TEXT DEFAULT 'New',
            priority TEXT DEFAULT 'Medium',
            follow_up_date TEXT DEFAULT '',
            last_contacted TEXT DEFAULT '',
            value REAL DEFAULT 0,
            notes TEXT DEFAULT '',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    existing = _column_names(conn, "leads")
    lead_migrations = {
        "company": "ALTER TABLE leads ADD COLUMN company TEXT DEFAULT ''",
        "priority": "ALTER TABLE leads ADD COLUMN priority TEXT DEFAULT 'Medium'",
        "follow_up_date": "ALTER TABLE leads ADD COLUMN follow_up_date TEXT DEFAULT ''",
        "last_contacted": "ALTER TABLE leads ADD COLUMN last_contacted TEXT DEFAULT ''",
    }

    for column, statement in lead_migrations.items():
        if column not in existing:
            cur.execute(statement)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS saved_outputs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            tool_name TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    """)

    conn.commit()
    conn.close()


def create_user(email: str, password_hash: str) -> tuple[bool, str]:
    conn = connect()
    try:
        cur = conn.cursor()
        cur.execute(
            """
            INSERT INTO users (
                email, password_hash, plan, plan_status,
                stripe_customer_id, stripe_subscription_id
            )
            VALUES (?, ?, 'Starter', 'test', '', '')
            """,
            (email.lower().strip(), password_hash),
        )
        user_id = cur.lastrowid
        cur.execute(
            "INSERT INTO business_profiles (user_id, business_name) VALUES (?, ?)",
            (user_id, "My Business"),
        )
        conn.commit()
        return True, "Account created."
    except sqlite3.IntegrityError:
        return False, "An account with that email already exists."
    finally:
        conn.close()


def get_user_by_email(email: str) -> Optional[dict]:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM users WHERE email = ?",
        (email.lower().strip(),),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def get_user_plan(user_id: int) -> dict:
    conn = connect()
    row = conn.execute(
        """
        SELECT plan, plan_status, stripe_customer_id, stripe_subscription_id
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    ).fetchone()
    conn.close()

    if not row:
        return {
            "plan": "Starter",
            "plan_status": "test",
            "stripe_customer_id": "",
            "stripe_subscription_id": "",
        }

    return {
        "plan": row["plan"] or "Starter",
        "plan_status": row["plan_status"] or "test",
        "stripe_customer_id": row["stripe_customer_id"] or "",
        "stripe_subscription_id": row["stripe_subscription_id"] or "",
    }


def update_user_plan(
    user_id: int,
    plan: str,
    status: str = "test",
    stripe_customer_id: str = "",
    stripe_subscription_id: str = "",
):
    allowed_plans = {"Starter", "Growth", "Pro"}
    if plan not in allowed_plans:
        raise ValueError("Invalid plan selected.")

    conn = connect()
    conn.execute(
        """
        UPDATE users
        SET plan = ?,
            plan_status = ?,
            stripe_customer_id = CASE
                WHEN ? != '' THEN ?
                ELSE stripe_customer_id
            END,
            stripe_subscription_id = CASE
                WHEN ? != '' THEN ?
                ELSE stripe_subscription_id
            END
        WHERE id = ?
        """,
        (
            plan,
            status,
            stripe_customer_id,
            stripe_customer_id,
            stripe_subscription_id,
            stripe_subscription_id,
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def clear_user_subscription(user_id: int):
    conn = connect()
    conn.execute(
        """
        UPDATE users
        SET plan = 'Starter',
            plan_status = 'cancelled',
            stripe_subscription_id = ''
        WHERE id = ?
        """,
        (user_id,),
    )
    conn.commit()
    conn.close()


def get_profile(user_id: int) -> dict:
    conn = connect()
    row = conn.execute(
        "SELECT * FROM business_profiles WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else {}


def update_profile(user_id: int, data: dict):
    conn = connect()
    conn.execute(
        """
        UPDATE business_profiles
        SET business_name=?, industry=?, location=?, services=?,
            ideal_customer=?, brand_voice=?, monthly_revenue=?,
            monthly_goal=?, marketing_budget=?, employees=?
        WHERE user_id=?
        """,
        (
            data["business_name"],
            data["industry"],
            data["location"],
            data["services"],
            data["ideal_customer"],
            data["brand_voice"],
            data["monthly_revenue"],
            data["monthly_goal"],
            data["marketing_budget"],
            data["employees"],
            user_id,
        ),
    )
    conn.commit()
    conn.close()


def add_lead(
    user_id: int,
    name: str,
    email: str,
    phone: str,
    company: str,
    status: str,
    priority: str,
    follow_up_date: str,
    last_contacted: str,
    value: float,
    notes: str,
):
    conn = connect()
    conn.execute(
        """
        INSERT INTO leads (
            user_id, name, email, phone, company, status, priority,
            follow_up_date, last_contacted, value, notes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id, name, email, phone, company, status, priority,
            follow_up_date, last_contacted, value, notes
        ),
    )
    conn.commit()
    conn.close()


def update_lead(
    user_id: int,
    lead_id: int,
    name: str,
    email: str,
    phone: str,
    company: str,
    status: str,
    priority: str,
    follow_up_date: str,
    last_contacted: str,
    value: float,
    notes: str,
):
    conn = connect()
    conn.execute(
        """
        UPDATE leads
        SET name=?, email=?, phone=?, company=?, status=?, priority=?,
            follow_up_date=?, last_contacted=?, value=?, notes=?
        WHERE id=? AND user_id=?
        """,
        (
            name, email, phone, company, status, priority,
            follow_up_date, last_contacted, value, notes,
            lead_id, user_id
        ),
    )
    conn.commit()
    conn.close()


def get_leads(user_id: int) -> list[dict]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM leads WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]


def delete_lead(user_id: int, lead_id: int):
    conn = connect()
    conn.execute(
        "DELETE FROM leads WHERE id = ? AND user_id = ?",
        (lead_id, user_id),
    )
    conn.commit()
    conn.close()


def save_output(user_id: int, tool_name: str, content: str):
    conn = connect()
    conn.execute(
        "INSERT INTO saved_outputs (user_id, tool_name, content) VALUES (?, ?, ?)",
        (user_id, tool_name, content),
    )
    conn.commit()
    conn.close()


def get_saved_outputs(user_id: int) -> list[dict]:
    conn = connect()
    rows = conn.execute(
        "SELECT * FROM saved_outputs WHERE user_id = ? ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(row) for row in rows]
