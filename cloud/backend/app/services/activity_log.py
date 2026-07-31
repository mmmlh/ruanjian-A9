from app.database.connection import get_db


def write_activity(
    event_type: str,
    title: str,
    detail: str,
    source: str,
    device_id: int | None = None,
    user_id: int | None = None,
) -> None:
    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO activity_log (event_type, title, detail, source, device_id, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (event_type, title, detail, source, device_id, user_id),
        )
