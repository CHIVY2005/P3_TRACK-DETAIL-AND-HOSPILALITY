from datetime import datetime
from typing import Any, Dict, List, MutableMapping, Optional, TypedDict

from sqlalchemy.orm import Session

from app.config import get_agent_config
from app.db import models
from app.agents.margin_guardian.margin_guardian_tools import compute_margin_scenarios, propose_price_match
from app.agents.shared.runtime_support import (
    append_log,
    dumps_json,
    get_langfuse_client,
    run_agent_tool,
    timestamp,
)
from app.agents.supplier_negotiator.supplier_negotiator_agent import draft_supplier_negotiation


class AgentState(TypedDict):
    product_id: int
    competitor_price_id: int
    cost_price: float
    guardian_price: float
    competitor_price: float
    competitor_name: str
    brand_name: str
    target_margin: float
    strategy: str
    decision_reason: str
    negotiation_context: str
    email_draft: Dict[str, str]
    logs: List[str]
    actions_created: List[Dict[str, Any]]
    tool_events: List[Dict[str, Any]]


def run_margin_analysis(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    metrics = run_agent_tool(
        state,
        "compute_margin_scenarios",
        {
            "product_id": state["product_id"],
            "guardian_price": state["guardian_price"],
            "competitor_price": state["competitor_price"],
            "cost_price": state["cost_price"],
        },
        lambda: compute_margin_scenarios(state),
    )

    state["target_margin"] = metrics["margin_if_matched_pct"]
    append_log(
        state,
        (
            f"  Guardian {state['guardian_price']:,.0f} VND | Cost {state['cost_price']:,.0f} VND | "
            f"Competitor {state['competitor_price']:,.0f} VND"
        ),
    )
    append_log(
        state,
        (
            f"  Current margin {metrics['current_margin_pct']:.1f}% | "
            f"Margin if matched {metrics['margin_if_matched_pct']:.1f}% | "
            f"Gap {metrics['price_gap_pct']:.1f}%"
        ),
    )
    return state


def determine_strategy(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    append_log(state, f"[{timestamp()}] [Node: determine_strategy] Selecting strategy")
    cfg = get_agent_config()
    min_margin_pct = cfg.get("min_margin", 0.15) * 100.0
    custom_instruction = cfg.get("custom_instruction", "")
    target_margin = state["target_margin"]
    strategy = "match" if target_margin >= min_margin_pct else "negotiate"
    reason = (
        f"Rule-based decision with target margin {target_margin:.1f}% "
        f"and floor {min_margin_pct:.1f}%."
    )
    if custom_instruction:
        reason = f"{reason} Instruction: {custom_instruction}"

    state["strategy"] = strategy
    state["decision_reason"] = reason
    append_log(state, f"  [Decision] {strategy.upper()} | {reason}")
    return state


def apply_auto_match(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    proposal = run_agent_tool(
        state,
        "adjust_system_price",
        {
            "product_id": state["product_id"],
            "guardian_price": state["guardian_price"],
            "competitor_price": state["competitor_price"],
        },
        lambda: propose_price_match(state),
    )

    actions = list(state.get("actions_created", []))
    actions.append(
        {
            "action_type": "AUTO_PRICE_MATCH",
            "description": (
                f"Propose matching Guardian price with {state['competitor_name']} from "
                f"{state['guardian_price']:,.0f} to {state['competitor_price']:,.0f} VND."
            ),
            "data": dumps_json(
                {
                    **proposal,
                    "decision_summary": {
                        "strategy": state["strategy"],
                        "reason": state["decision_reason"],
                        "competitor_name": state["competitor_name"],
                        "guardian_price": state["guardian_price"],
                        "competitor_price": state["competitor_price"],
                        "margin_if_matched_pct": state["target_margin"],
                    },
                }
            ),
        }
    )
    state["actions_created"] = actions
    append_log(state, f"  [Action] Price-match proposal created for {state['competitor_name']}.")
    return state


def run_margin_guardian_for_alert(db: Session, alert: models.Alert) -> Dict[str, Any]:
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "No product"}

    latest_price = (
        db.query(models.CompetitorPrice)
        .filter(models.CompetitorPrice.product_id == product.id)
        .order_by(models.CompetitorPrice.scraped_at.desc())
        .first()
    )
    if not latest_price or latest_price.net_price is None:
        return {"status": "skipped", "reason": "No competitor prices"}

    brand_name = (product.name.split()[0:3] and " ".join(product.name.split()[0:3])) or product.category
    initial_state = AgentState(
        product_id=product.id,
        competitor_price_id=latest_price.id,
        cost_price=product.cost_price or (product.guardian_price * 0.60),
        guardian_price=product.guardian_price,
        competitor_price=latest_price.net_price,
        competitor_name=latest_price.competitor_name,
        brand_name=brand_name,
        target_margin=0.0,
        strategy="maintain",
        decision_reason="",
        negotiation_context="",
        email_draft={},
        logs=[f"[Margin Guardian Starting] Optimizing alert ID {alert.id}"],
        actions_created=[],
        tool_events=[],
    )

    langfuse = get_langfuse_client()
    if langfuse:
        with langfuse.start_as_current_observation(
            as_type="span",
            name="pricing-alert-run",
            input={
                "alert_id": alert.id,
                "product_id": product.id,
                "product_name": product.name,
            },
        ) as span:
            result = _execute_margin_guardian_graph(initial_state)
            metrics = next(
                (
                    event.get("output", {})
                    for event in result.get("tool_events", [])
                    if event.get("name") == "compute_margin_scenarios"
                ),
                {},
            )
            span.update(
                output={
                    "strategy": result.get("strategy"),
                    "decision_summary": {
                        "strategy": result.get("strategy"),
                        "reason": result.get("decision_reason"),
                        "competitor_name": result.get("competitor_name"),
                        "guardian_price": result.get("guardian_price"),
                        "competitor_price": result.get("competitor_price"),
                        "current_margin_pct": metrics.get("current_margin_pct"),
                        "margin_if_matched_pct": metrics.get("margin_if_matched_pct"),
                        "price_gap_pct": metrics.get("price_gap_pct"),
                    },
                    "tool_events": len(result.get("tool_events", [])),
                    "actions_created": len(result.get("actions_created", [])),
                }
            )
            return result

    return _execute_margin_guardian_graph(initial_state)


def _execute_margin_guardian_graph(initial_state: AgentState) -> Dict[str, Any]:
    try:
        from langgraph.graph import END, StateGraph

        workflow = StateGraph(AgentState)
        workflow.add_node("margin_analysis", run_margin_analysis)
        workflow.add_node("determine_strategy", determine_strategy)
        workflow.add_node("apply_auto_match", apply_auto_match)
        workflow.add_node("supplier_negotiation", draft_supplier_negotiation)
        workflow.set_entry_point("margin_analysis")
        workflow.add_edge("margin_analysis", "determine_strategy")

        def router_edge(state: AgentState):
            return "apply_auto_match" if state["strategy"] == "match" else "supplier_negotiation"

        workflow.add_conditional_edges(
            "determine_strategy",
            router_edge,
            {
                "apply_auto_match": "apply_auto_match",
                "supplier_negotiation": "supplier_negotiation",
            },
        )
        workflow.add_edge("apply_auto_match", END)
        workflow.add_edge("supplier_negotiation", END)

        app_graph = workflow.compile()
        return app_graph.invoke(initial_state)
    except Exception as exc:
        print(f"LangGraph execution failed: {exc}. Running fallback sequence...")
        state = run_margin_analysis(initial_state)
        state = determine_strategy(state)
        if state["strategy"] == "match":
            state = apply_auto_match(state)
        else:
            state = draft_supplier_negotiation(state)
        return state
