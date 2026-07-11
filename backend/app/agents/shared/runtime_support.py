import os
import json
import threading
import time
from functools import lru_cache
from datetime import datetime, timezone
from typing import Any, Callable, Dict, MutableMapping, Optional


AgentStateLike = MutableMapping[str, Any]
_runtime_lock = threading.Lock()


def _utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _empty_agent_states() -> Dict[str, Dict[str, Any]]:
    return {
        "orchestrator": {"status": "idle", "phase": "idle", "thought": None, "tool": None, "updated_at": None},
        "market_observer": {"status": "idle", "phase": "idle", "thought": None, "tool": None, "updated_at": None},
        "margin_guardian": {"status": "idle", "phase": "idle", "thought": None, "tool": None, "updated_at": None},
        "supplier_negotiator": {"status": "idle", "phase": "idle", "thought": None, "tool": None, "updated_at": None},
    }


_runtime_snapshot: Dict[str, Any] = {
    "run_id": None,
    "active_agent": None,
    "phase": "idle",
    "current_thought": None,
    "current_tool": None,
    "tool_status": None,
    "current_product": None,
    "progress": {"completed": 0, "total": 0},
    "updated_at": None,
    "recent_tools": [],
    "activity": [],
    "agent_states": _empty_agent_states(),
}


def _ensure_langfuse_env_aliases() -> None:
    host = os.getenv("LANGFUSE_HOST", "").strip()
    base_url = os.getenv("LANGFUSE_BASE_URL", "").strip()

    if base_url and not host:
        os.environ["LANGFUSE_HOST"] = base_url
    elif host and not base_url:
        os.environ["LANGFUSE_BASE_URL"] = host


def _has_langfuse_credentials() -> bool:
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "").strip()
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "").strip()
    host = os.getenv("LANGFUSE_HOST", "").strip() or os.getenv("LANGFUSE_BASE_URL", "").strip()
    return bool(
        public_key
        and secret_key
        and host
        and "your_langfuse" not in public_key
        and "your_langfuse" not in secret_key
    )


@lru_cache(maxsize=1)
def get_langfuse_client():
    _ensure_langfuse_env_aliases()
    if not _has_langfuse_credentials():
        return None

    try:
        from langfuse import get_client

        return get_client()
    except Exception as exc:
        print(f"Langfuse client initialization failed: {exc}")
        return None


def flush_langfuse() -> None:
    client = get_langfuse_client()
    if not client:
        return

    try:
        client.flush()
    except Exception as exc:
        print(f"Langfuse flush failed: {exc}")


def shutdown_langfuse() -> None:
    client = get_langfuse_client()
    if not client:
        return

    try:
        client.shutdown()
    except Exception as exc:
        print(f"Langfuse shutdown failed: {exc}")


def timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def reset_live_runtime(run_id: Optional[str] = None, total_steps: int = 0) -> None:
    with _runtime_lock:
        _runtime_snapshot.update(
            {
                "run_id": run_id,
                "active_agent": None,
                "phase": "idle",
                "current_thought": None,
                "current_tool": None,
                "tool_status": None,
                "current_product": None,
                "progress": {"completed": 0, "total": max(total_steps, 0)},
                "updated_at": _utc_iso(),
                "recent_tools": [],
                "activity": [],
                "agent_states": _empty_agent_states(),
            }
        )


def update_live_runtime(**changes: Any) -> None:
    with _runtime_lock:
        if "recent_tools" in changes and changes["recent_tools"] is None:
            changes["recent_tools"] = []
        _runtime_snapshot.update(changes)
        now = _utc_iso()
        _runtime_snapshot["updated_at"] = now
        active_agent = _runtime_snapshot.get("active_agent")
        if active_agent:
            agent_state = _runtime_snapshot.setdefault("agent_states", {}).setdefault(active_agent, {})
            if "phase" in changes:
                agent_state["phase"] = changes["phase"]
            if "current_thought" in changes:
                agent_state["thought"] = changes["current_thought"]
            if "current_tool" in changes:
                agent_state["tool"] = changes["current_tool"]
            agent_state["updated_at"] = now


def get_live_runtime_snapshot() -> Dict[str, Any]:
    with _runtime_lock:
        snapshot = dict(_runtime_snapshot)
        snapshot["recent_tools"] = list(_runtime_snapshot.get("recent_tools", []))
        snapshot["activity"] = list(_runtime_snapshot.get("activity", []))
        snapshot["progress"] = dict(_runtime_snapshot.get("progress", {}))
        snapshot["agent_states"] = {
            name: dict(state) for name, state in _runtime_snapshot.get("agent_states", {}).items()
        }
        return snapshot


def set_active_agent(agent_name: str, phase: Optional[str] = None, thought: Optional[str] = None) -> None:
    now = _utc_iso()
    with _runtime_lock:
        previous_agent = _runtime_snapshot.get("active_agent")
        if previous_agent and previous_agent != agent_name:
            previous_state = _runtime_snapshot.setdefault("agent_states", {}).setdefault(previous_agent, {})
            previous_state["status"] = "completed"
            previous_state["updated_at"] = now
            _runtime_snapshot["current_tool"] = None
            _runtime_snapshot["tool_status"] = None

        _runtime_snapshot["active_agent"] = agent_name
        if phase is not None:
            _runtime_snapshot["phase"] = phase
        if thought is not None:
            _runtime_snapshot["current_thought"] = thought
        _runtime_snapshot["updated_at"] = now

        agent_state = _runtime_snapshot.setdefault("agent_states", {}).setdefault(agent_name, {})
        agent_state.update(
            {
                "status": "active",
                "phase": phase or agent_state.get("phase", "thinking"),
                "thought": thought or agent_state.get("thought"),
                "tool": _runtime_snapshot.get("current_tool"),
                "updated_at": now,
            }
        )
        _runtime_snapshot.setdefault("activity", []).append(
            {
                "agent": agent_name,
                "phase": phase or agent_state.get("phase", "thinking"),
                "kind": "thought",
                "status": "active",
                "label": thought or f"{agent_name} is active.",
                "at": now,
            }
        )
        _runtime_snapshot["activity"] = _runtime_snapshot["activity"][-40:]


def set_current_thought(thought: str) -> None:
    update_live_runtime(current_thought=thought)


def record_live_activity(
    label: str,
    kind: str = "status",
    status: str = "info",
    agent: Optional[str] = None,
    phase: Optional[str] = None,
) -> None:
    """Store a short audit-safe activity item for the live Agent Workspace."""
    now = _utc_iso()
    with _runtime_lock:
        active_agent = agent or _runtime_snapshot.get("active_agent")
        _runtime_snapshot.setdefault("activity", []).append(
            {
                "agent": active_agent,
                "phase": phase or _runtime_snapshot.get("phase"),
                "kind": kind,
                "status": status,
                "label": label,
                "at": now,
            }
        )
        _runtime_snapshot["activity"] = _runtime_snapshot["activity"][-40:]


def append_log(state: AgentStateLike, message: str) -> None:
    logs = list(state.get("logs", []))
    logs.append(message)
    state["logs"] = logs
    normalized = message.strip()
    if "THOUGHT:" in normalized:
        set_current_thought(normalized.split("THOUGHT:", 1)[1].strip())


def append_tool_event(
    state: AgentStateLike,
    name: str,
    status: str,
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]] = None,
) -> None:
    events = list(state.get("tool_events", []))
    event = {
        "name": name,
        "status": status,
        "input": input_payload,
        "output": output_payload or {},
        "at": _utc_iso(),
        "agent": get_live_runtime_snapshot().get("active_agent"),
    }
    events.append(event)
    state["tool_events"] = events
    recent_tools = list(get_live_runtime_snapshot().get("recent_tools", []))
    recent_tools.append(event)
    update_live_runtime(recent_tools=recent_tools[-8:])


def run_agent_tool(
    state: AgentStateLike,
    name: str,
    input_payload: Dict[str, Any],
    func: Callable[[], Any],
):
    append_log(state, f"[{timestamp()}] [Tool: {name}] Start")
    update_live_runtime(current_tool=name, tool_status="running", phase="tool_execution")
    record_live_activity(f"Running {name}", kind="tool", status="running")
    started_at = time.perf_counter()
    client = get_langfuse_client()

    if client:
        with client.start_as_current_observation(
            as_type="tool",
            name=name,
            input=input_payload,
        ) as observation:
            try:
                result = func()
                observation.update(output=result)
                append_tool_event(state, name, "success", input_payload, _normalize_tool_output(result))
                append_log(state, f"  [Tool Result] {name} completed")
                update_live_runtime(current_tool=name, tool_status="success")
                record_live_activity(
                    f"{name} completed in {time.perf_counter() - started_at:.2f}s",
                    kind="tool",
                    status="success",
                )
                return result
            except Exception as exc:
                observation.update(output={"error": str(exc)})
                append_tool_event(state, name, "error", input_payload, {"error": str(exc)})
                append_log(state, f"  [Tool Error] {name}: {exc}")
                update_live_runtime(current_tool=name, tool_status="error", current_thought=f"Tool {name} failed: {exc}")
                record_live_activity(f"{name} failed: {exc}", kind="tool", status="error")
                raise

    try:
        result = func()
        append_tool_event(state, name, "success", input_payload, _normalize_tool_output(result))
        append_log(state, f"  [Tool Result] {name} completed")
        update_live_runtime(current_tool=name, tool_status="success")
        record_live_activity(
            f"{name} completed in {time.perf_counter() - started_at:.2f}s",
            kind="tool",
            status="success",
        )
        return result
    except Exception as exc:
        append_tool_event(state, name, "error", input_payload, {"error": str(exc)})
        append_log(state, f"  [Tool Error] {name}: {exc}")
        update_live_runtime(current_tool=name, tool_status="error", current_thought=f"Tool {name} failed: {exc}")
        record_live_activity(f"{name} failed: {exc}", kind="tool", status="error")
        raise


def dumps_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _normalize_tool_output(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    return {"result": result}
