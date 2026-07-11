"""Keep the remote database connection warm.

Connecting to the Supabase pooler pays a ~3s TLS + auth handshake. If the pool
sits idle the provider drops the connection and the next user request eats that
handshake again. A tiny periodic ping keeps at least one pooled connection alive
so cold-start latency stays off the request path.
"""

import threading

from sqlalchemy import text

from app.db.session import engine

_stop_event = threading.Event()
_thread = None
PING_INTERVAL_SECONDS = 240  # 4 minutes, comfortably under typical idle timeouts


def _ping() -> None:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    except Exception as exc:  # pragma: no cover - best effort keep-alive
        print(f"DB keep-alive ping failed: {exc}")


def start_db_keepalive() -> None:
    global _thread
    if _thread and _thread.is_alive():
        return
    _ping()  # warm the pool immediately at startup
    _stop_event.clear()

    def _loop() -> None:
        while not _stop_event.wait(PING_INTERVAL_SECONDS):
            _ping()

    _thread = threading.Thread(target=_loop, name="db-keepalive", daemon=True)
    _thread.start()


def stop_db_keepalive() -> None:
    _stop_event.set()
