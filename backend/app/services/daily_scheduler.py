import threading
from datetime import datetime
from typing import Optional

from app.config import settings
from app.services.agent_runtime import create_agent_task, get_agent_runtime_status, run_agent_task


_scheduler_thread: Optional[threading.Thread] = None
_stop_event = threading.Event()
_scheduler_lock = threading.Lock()
_scheduler_status = {
    "enabled": False,
    "interval_seconds": 0,
    "started_at": None,
    "last_tick_at": None,
    "last_run_task_id": None,
    "last_run_started_at": None,
    "last_run_completed_at": None,
}


def start_daily_scheduler() -> None:
    global _scheduler_thread

    if not settings.AGENT_SCHEDULER_ENABLED:
        with _scheduler_lock:
            _scheduler_status["enabled"] = False
            _scheduler_status["interval_seconds"] = settings.AGENT_SCHEDULE_INTERVAL_SECONDS
        return

    if _scheduler_thread and _scheduler_thread.is_alive():
        return

    _stop_event.clear()
    with _scheduler_lock:
        _scheduler_status["enabled"] = True
        _scheduler_status["interval_seconds"] = settings.AGENT_SCHEDULE_INTERVAL_SECONDS
        _scheduler_status["started_at"] = datetime.utcnow().isoformat()

    _scheduler_thread = threading.Thread(target=_scheduler_loop, name="guardian-daily-scheduler", daemon=True)
    _scheduler_thread.start()


def stop_daily_scheduler() -> None:
    _stop_event.set()


def get_scheduler_status() -> dict:
    with _scheduler_lock:
        status = dict(_scheduler_status)
    status["agent_runtime"] = get_agent_runtime_status()
    return status


def _scheduler_loop() -> None:
    interval = max(settings.AGENT_SCHEDULE_INTERVAL_SECONDS, 60)

    while not _stop_event.wait(interval):
        now = datetime.utcnow().isoformat()
        with _scheduler_lock:
            _scheduler_status["last_tick_at"] = now

        if get_agent_runtime_status().get("is_running"):
            continue

        task = create_agent_task(
            source="scheduler",
            objective="[SCHEDULER] Daily autonomous pricing refresh and recommendation cycle.",
        )
        with _scheduler_lock:
            _scheduler_status["last_run_task_id"] = task.id
            _scheduler_status["last_run_started_at"] = datetime.utcnow().isoformat()

        started = run_agent_task(task.id, refresh_market_data=True, source="scheduler")
        if started:
            with _scheduler_lock:
                _scheduler_status["last_run_completed_at"] = datetime.utcnow().isoformat()
