import threading
from datetime import datetime
from typing import Optional

from app.db import models
from app.db.session import SessionLocal
from app.agents.shared.runtime_support import (
    flush_langfuse,
    get_langfuse_client,
    get_live_runtime_snapshot,
    reset_live_runtime,
    update_live_runtime,
)
from app.services.agent_engine import run_agentic_optimization_loop


_agent_lock = threading.Lock()
_state_lock = threading.Lock()
_is_agent_running = False
_last_started_at: Optional[str] = None
_last_completed_at: Optional[str] = None
_last_trigger_source: Optional[str] = None
_last_error: Optional[str] = None
_last_trace_id: Optional[str] = None
_last_trace_url: Optional[str] = None


def is_agent_running() -> bool:
    with _state_lock:
        return _is_agent_running


def get_agent_runtime_status() -> dict:
    with _state_lock:
        return {
            "is_running": _is_agent_running,
            "last_started_at": _last_started_at,
            "last_completed_at": _last_completed_at,
            "last_trigger_source": _last_trigger_source,
            "last_error": _last_error,
            "last_trace_id": _last_trace_id,
            "last_trace_url": _last_trace_url,
            "live_runtime": get_live_runtime_snapshot(),
        }


def create_agent_task(source: str, objective: Optional[str] = None) -> models.AgentTask:
    db = SessionLocal()
    try:
        task = models.AgentTask(
            objective=objective
            or f"[{source.upper()}] Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index.",
            status="Pending",
            logs=f"[Agent Queued] Source={source}. Waiting to start autonomous watchtower run...",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
        db.expunge(task)
        return task
    finally:
        db.close()


def run_agent_task(task_id: int, refresh_market_data: bool, source: str) -> bool:
    global _is_agent_running, _last_started_at, _last_completed_at, _last_trigger_source, _last_error, _last_trace_id, _last_trace_url

    acquired = _agent_lock.acquire(blocking=False)
    if not acquired:
        return False

    with _state_lock:
        _is_agent_running = True
        _last_started_at = datetime.utcnow().isoformat()
        _last_trigger_source = source
        _last_error = None
        _last_trace_id = None
        _last_trace_url = None
    reset_live_runtime(run_id=f"task-{task_id}")
    update_live_runtime(
        active_agent="orchestrator",
        phase="queued",
        current_thought=f"Task #{task_id} accepted from {source}. Preparing pricing cycle.",
    )

    db = SessionLocal()
    try:
        def run_and_validate():
            result = run_agentic_optimization_loop(
                db,
                task_id=task_id,
                refresh_market_data=refresh_market_data,
            )
            if result.status == "Failed":
                failure_log = (result.logs or "Agent task failed.").splitlines()[-1]
                raise RuntimeError(failure_log)
            return result

        client = get_langfuse_client()
        if client:
            with client.start_as_current_observation(
                as_type="span",
                name="agent-runtime-run",
                input={
                    "task_id": task_id,
                    "source": source,
                    "refresh_market_data": refresh_market_data,
                },
            ) as span:
                result = run_and_validate()
                trace_id = client.get_current_trace_id()
                trace_url = client.get_trace_url() if trace_id else None
                with _state_lock:
                    _last_trace_id = trace_id
                    _last_trace_url = trace_url
                span.update(
                    output={
                        "task_id": task_id,
                        "source": source,
                        "completed_at": datetime.utcnow().isoformat(),
                        "trace_id": trace_id,
                        "trace_url": trace_url,
                    }
                )
        else:
            run_and_validate()
    except Exception as exc:
        with _state_lock:
            _last_error = str(exc)
        update_live_runtime(
            active_agent="orchestrator",
            phase="failed",
            current_thought=f"Run failed: {exc}",
            tool_status="error",
        )
        print(f"Error in agent task ({source}): {exc}")
    finally:
        db.close()
        flush_langfuse()
        with _state_lock:
            _is_agent_running = False
            _last_completed_at = datetime.utcnow().isoformat()
        if _last_error:
            update_live_runtime(phase="failed")
        else:
            update_live_runtime(
                active_agent="orchestrator",
                phase="completed",
                current_tool=None,
                tool_status="success",
                current_thought="Decision cycle completed. Waiting for the next trigger.",
            )
        _agent_lock.release()

    return True
