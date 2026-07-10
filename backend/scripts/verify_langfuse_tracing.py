import os
import sys
import time
from pathlib import Path

import requests
from dotenv import load_dotenv


ROOT_DIR = Path(__file__).resolve().parents[2]
load_dotenv(ROOT_DIR / ".env")


def main() -> int:
    base_url = os.getenv("BACKEND_BASE_URL", "http://127.0.0.1:8001").rstrip("/")
    api_base = f"{base_url}/api/v1"

    run_response = requests.post(
        f"{api_base}/agent/run",
        json={"refresh_market_data": False},
        timeout=20,
    )
    run_response.raise_for_status()
    task = run_response.json()
    task_id = task["id"]
    print(f"Triggered agent task {task_id}")

    runtime_status = None
    for _ in range(30):
        time.sleep(2)
        runtime_response = requests.get(f"{api_base}/agent/runtime-status", timeout=20)
        runtime_response.raise_for_status()
        runtime_status = runtime_response.json()
        if not runtime_status["agent"]["is_running"]:
            break

    task_response = requests.get(f"{api_base}/agent/tasks/{task_id}", timeout=20)
    task_response.raise_for_status()
    final_task = task_response.json()

    trace_url = (runtime_status or {}).get("agent", {}).get("last_trace_url")
    trace_id = (runtime_status or {}).get("agent", {}).get("last_trace_id")

    print(f"Task status: {final_task['status']}")
    print(f"Trace ID: {trace_id}")
    print(f"Trace URL: {trace_url}")
    if final_task.get("logs"):
        print("Last log line:")
        print(final_task["logs"].splitlines()[-1])

    return 0 if trace_url else 1


if __name__ == "__main__":
    raise SystemExit(main())
