"""Explicit memory proposals, deterministic selection, and reversible journal."""

from .storage import Store, utc_now


def propose(store: Store, body: str, salience: int = 5) -> int:
    text = body.strip()
    if not text:
        raise ValueError("memory proposal must not be empty")
    if not 1 <= salience <= 10:
        raise ValueError("salience must be between 1 and 10")
    now = utc_now()
    cursor = store.connection.execute(
        "INSERT INTO memory_items(body, salience, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (text, salience, now, now),
    )
    memory_id = int(cursor.lastrowid)
    store.connection.execute(
        "INSERT INTO memory_events(memory_id, action, reason, created_at) VALUES (?, 'proposed', ?, ?)",
        (memory_id, "explicit owner proposal", now),
    )
    store.connection.commit()
    return memory_id


def cycle(store: Store, limit: int = 3) -> dict[str, list[int]]:
    if limit < 1:
        raise ValueError("selection limit must be positive")
    db, now = store.connection, utc_now()
    rows = db.execute(
        "SELECT id, salience FROM memory_items WHERE status='active' ORDER BY salience DESC, id ASC"
    ).fetchall()
    kept = [int(row["id"]) for row in rows[:limit]]
    forgotten = [int(row["id"]) for row in rows[limit:]]
    for item_id in kept:
        db.execute("UPDATE memory_items SET updated_at=? WHERE id=?", (now, item_id))
        db.execute(
            "INSERT INTO memory_events(memory_id, action, reason, created_at) VALUES (?, 'kept', ?, ?)",
            (item_id, "deterministic salience selection", now),
        )
    for item_id in forgotten:
        db.execute(
            "UPDATE memory_items SET status='forgotten', forgotten_at=?, updated_at=? WHERE id=?",
            (now, now, item_id),
        )
        db.execute(
            "INSERT INTO memory_events(memory_id, action, reason, created_at) VALUES (?, 'forgotten', ?, ?)",
            (item_id, "outside the active selection limit", now),
        )
    db.commit()
    return {"kept": kept, "forgotten": forgotten}


def restore(store: Store, memory_id: int) -> None:
    db, now = store.connection, utc_now()
    cursor = db.execute(
        "UPDATE memory_items SET status='active', forgotten_at=NULL, updated_at=? "
        "WHERE id=? AND status='forgotten'",
        (now, memory_id),
    )
    if cursor.rowcount != 1:
        db.rollback()
        raise ValueError("memory item is missing or is not forgotten")
    db.execute(
        "INSERT INTO memory_events(memory_id, action, reason, created_at) VALUES (?, 'restored', ?, ?)",
        (memory_id, "owner reversed a forgetting decision", now),
    )
    db.commit()


def active_items(store: Store) -> list[dict[str, object]]:
    return [dict(row) for row in store.connection.execute(
        "SELECT id, body, salience FROM memory_items WHERE status='active' ORDER BY salience DESC, id"
    )]
