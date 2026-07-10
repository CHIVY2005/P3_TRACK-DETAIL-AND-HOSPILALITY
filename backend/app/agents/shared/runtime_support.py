import os
import json
from functools import lru_cache
from datetime import datetime
from typing import Any, Callable, Dict, MutableMapping, Optional


AgentStateLike = MutableMapping[str, Any]


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


def append_log(state: AgentStateLike, message: str) -> None:
    logs = list(state.get("logs", []))
    logs.append(message)
    state["logs"] = logs


def append_tool_event(
    state: AgentStateLike,
    name: str,
    status: str,
    input_payload: Dict[str, Any],
    output_payload: Optional[Dict[str, Any]] = None,
) -> None:
    events = list(state.get("tool_events", []))
    events.append(
        {
            "name": name,
            "status": status,
            "input": input_payload,
            "output": output_payload or {},
            "at": datetime.utcnow().isoformat(),
        }
    )
    state["tool_events"] = events


def run_agent_tool(
    state: AgentStateLike,
    name: str,
    input_payload: Dict[str, Any],
    func: Callable[[], Any],
):
    append_log(state, f"[{timestamp()}] [Tool: {name}] Start")
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
                return result
            except Exception as exc:
                observation.update(output={"error": str(exc)})
                append_tool_event(state, name, "error", input_payload, {"error": str(exc)})
                append_log(state, f"  [Tool Error] {name}: {exc}")
                raise

    result = func()
    append_tool_event(state, name, "success", input_payload, _normalize_tool_output(result))
    append_log(state, f"  [Tool Result] {name} completed")
    return result


def dumps_json(data: Dict[str, Any]) -> str:
    return json.dumps(data, ensure_ascii=False)


def _normalize_tool_output(result: Any) -> Dict[str, Any]:
    if isinstance(result, dict):
        return result
    return {"result": result}
