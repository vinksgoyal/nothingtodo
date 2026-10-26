import hashlib
import re
import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Optional

from core.models import Verdict


DB_PATH = Path("~/.local/share/nothingtodo/items.db").expanduser()


def _connect() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def init_db() -> None:
    with _connect() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS items (
                id INTEGER PRIMARY KEY,
                doc_hash TEXT UNIQUE,
                verdict_json TEXT NOT NULL,
                tier TEXT NOT NULL,
                first_seen DATE NOT NULL,
                deadline DATE,
                snoozes INTEGER DEFAULT 0,
                status TEXT DEFAULT 'open'
            )
            """
        )


def compute_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.lower()).strip()[:500]
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def exists(doc_hash: str) -> bool:
    """Return whether an item with the given document hash exists."""
    init_db()
    with _connect() as connection:
        row = connection.execute(
            "SELECT 1 FROM items WHERE doc_hash = ? LIMIT 1",
            (doc_hash,),
        ).fetchone()
    return row is not None


def upsert(doc_hash: str, verdict: Verdict, tier: str) -> int:
    init_db()
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO items (doc_hash, verdict_json, tier, first_seen, deadline)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(doc_hash) DO UPDATE SET
                verdict_json = excluded.verdict_json,
                tier = excluded.tier,
                deadline = excluded.deadline
            """,
            (
                doc_hash,
                verdict.model_dump_json(),
                tier,
                date.today().isoformat(),
                verdict.deadline,
            ),
        )
        if cursor.lastrowid:
            return cursor.lastrowid
        row = connection.execute(
            "SELECT id FROM items WHERE doc_hash = ?",
            (doc_hash,),
        ).fetchone()
        return row["id"]


def prior_amounts() -> list[tuple[str, float]]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            "SELECT verdict_json FROM items WHERE verdict_json IS NOT NULL"
        ).fetchall()

    amounts: list[tuple[str, float]] = []
    for row in rows:
        verdict = Verdict.model_validate_json(row["verdict_json"])
        if verdict.amount_due is not None:
            amounts.append((verdict.document_type, verdict.amount_due))
    return amounts


def open_items() -> list[dict]:
    init_db()
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT id, verdict_json, tier, first_seen, deadline, snoozes
            FROM items
            WHERE status = 'open'
            """
        ).fetchall()

    return [
        {
            "id": row["id"],
            "verdict": Verdict.model_validate_json(row["verdict_json"]),
            "tier": row["tier"],
            "first_seen": row["first_seen"],
            "deadline": row["deadline"],
            "snoozes": row["snoozes"],
        }
        for row in rows
    ]


def snooze(item_id: int) -> int:
    init_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE items SET snoozes = snoozes + 1 WHERE id = ?",
            (item_id,),
        )
        row = connection.execute(
            "SELECT snoozes FROM items WHERE id = ?",
            (item_id,),
        ).fetchone()
    if row is None:
        raise ValueError(f"Item not found: {item_id}")
    return row["snoozes"]


def resolve(item_id: int) -> None:
    init_db()
    with _connect() as connection:
        connection.execute(
            "UPDATE items SET status = 'done' WHERE id = ?",
            (item_id,),
        )


def resurface_date(
    first_seen: date,
    snoozes: int,
    deadline: Optional[date],
) -> date:
    days = 2**snoozes
    if deadline is not None:
        days = min(days, (deadline - first_seen).days)
    return first_seen + timedelta(days=days)
