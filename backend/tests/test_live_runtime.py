from app.agents.shared import runtime_support


def test_live_runtime_tracks_agent_tool_and_audit_timeline(monkeypatch):
    monkeypatch.setenv("LANGFUSE_PUBLIC_KEY", "")
    monkeypatch.setenv("LANGFUSE_SECRET_KEY", "")
    runtime_support.get_langfuse_client.cache_clear()

    runtime_support.reset_live_runtime("test-run", total_steps=2)
    runtime_support.set_active_agent(
        "market_observer",
        phase="perceive",
        thought="Scanning the next catalog product.",
    )
    state = {"logs": [], "tool_events": []}

    result = runtime_support.run_agent_tool(
        state,
        "refresh_competitor_market",
        {"product_count": 2},
        lambda: {"products_refreshed": 2},
    )
    snapshot = runtime_support.get_live_runtime_snapshot()

    assert result == {"products_refreshed": 2}
    assert snapshot["run_id"] == "test-run"
    assert snapshot["active_agent"] == "market_observer"
    assert snapshot["current_tool"] == "refresh_competitor_market"
    assert snapshot["tool_status"] == "success"
    assert snapshot["recent_tools"][-1]["status"] == "success"
    assert snapshot["recent_tools"][-1]["agent"] == "market_observer"
    assert any(item["kind"] == "tool" for item in snapshot["activity"])
    assert snapshot["agent_states"]["market_observer"]["status"] == "active"


def test_live_runtime_marks_previous_agent_completed_on_handoff():
    runtime_support.reset_live_runtime("handoff-test")
    runtime_support.set_active_agent("market_observer", phase="sensemaking", thought="Signals ranked.")
    runtime_support.set_active_agent("margin_guardian", phase="reasoning", thought="Checking margin safety.")
    snapshot = runtime_support.get_live_runtime_snapshot()

    assert snapshot["active_agent"] == "margin_guardian"
    assert snapshot["agent_states"]["market_observer"]["status"] == "completed"
    assert snapshot["agent_states"]["margin_guardian"]["status"] == "active"
