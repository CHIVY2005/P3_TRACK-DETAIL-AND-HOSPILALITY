import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, TypedDict

from sqlalchemy.orm import Session

from app.config import get_agent_config
from app.db import models
from app.scraper.scraper_engine import run_scraper_for_all_products


def query_supplier_policy_rag(brand_name: str, query_text: str) -> str:
    openai_key = os.getenv("OPENAI_API_KEY", "")
    knowledge_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "..", "data", "knowledge", "supplier_policies.txt")
    )

    if not openai_key or "your_openai" in openai_key or not os.path.exists(knowledge_path):
        if "Roche-Posay" in brand_name:
            return "La Roche-Posay policy supports up to 20% cost protection for price-match defense. Contact: thao.nguyen@loreal.com."
        if "Bioderma" in brand_name:
            return "Bioderma policy supports a 12,000 VND credit note per unit when competitors undercut. Contact: lam.hoang@minhanhbeauty.vn."
        if "Anessa" in brand_name:
            return "Shiseido requires a special discount approval request within 48 hours. Contact: chi.linh@shiseido.com.vn."
        return f"Contact the brand representative for {brand_name} to negotiate cost protection."

    try:
        from llama_index.core import SimpleDirectoryReader, VectorStoreIndex
        from llama_index.core.settings import Settings
        from llama_index.llms.openai import OpenAI

        Settings.llm = OpenAI(model="gpt-4o-mini", api_key=openai_key)
        documents = SimpleDirectoryReader(input_files=[knowledge_path]).load_data()
        index = VectorStoreIndex.from_documents(documents)
        query_engine = index.as_query_engine()
        response = query_engine.query(
            f"For brand {brand_name}, summarize cost-protection policy, reimbursement clauses, or supplier contact details. "
            f"Question: {query_text}"
        )
        return str(response)
    except Exception as exc:
        print(f"LlamaIndex RAG query failed: {exc}")
        return f"RAG lookup failed. Contact the supplier representative for {brand_name} directly."


def get_langfuse_client():
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY", "")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY", "")
    if not public_key or not secret_key or "your_langfuse" in public_key or "your_langfuse" in secret_key:
        return None

    try:
        from langfuse import get_client

        client = get_client()
        return client if client.auth_check() else None
    except Exception as exc:
        print(f"Langfuse client initialization failed: {exc}")
        return None


def get_langfuse_callback():
    client = get_langfuse_client()
    if not client:
        return None

    try:
        from langfuse.langchain import CallbackHandler

        return CallbackHandler()
    except Exception as exc:
        print(f"Langfuse callback initialization failed: {exc}")
        return None


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
    negotiation_context: str
    email_draft: Dict[str, str]
    logs: List[str]
    actions_created: List[Dict[str, Any]]
    tool_events: List[Dict[str, Any]]


def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _append_log(state: AgentState, message: str) -> None:
    logs = list(state.get("logs", []))
    logs.append(message)
    state["logs"] = logs


def _append_tool_event(
    state: AgentState,
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


def _run_agent_tool(
    state: AgentState,
    name: str,
    input_payload: Dict[str, Any],
    func,
):
    _append_log(state, f"[{_timestamp()}] [Tool: {name}] Start")
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
                _append_tool_event(state, name, "success", input_payload, result if isinstance(result, dict) else {"result": result})
                _append_log(state, f"  [Tool Result] {name} completed")
                return result
            except Exception as exc:
                observation.update(output={"error": str(exc)})
                _append_tool_event(state, name, "error", input_payload, {"error": str(exc)})
                _append_log(state, f"  [Tool Error] {name}: {exc}")
                raise

    result = func()
    _append_tool_event(state, name, "success", input_payload, result if isinstance(result, dict) else {"result": result})
    _append_log(state, f"  [Tool Result] {name} completed")
    return result


def tool_compute_margin_scenarios(state: AgentState) -> Dict[str, Any]:
    guardian_price = state["guardian_price"]
    competitor_price = state["competitor_price"]
    cost_price = state["cost_price"]

    current_margin = ((guardian_price - cost_price) / guardian_price) * 100 if guardian_price else 0.0
    margin_if_matched = ((competitor_price - cost_price) / competitor_price) * 100 if competitor_price else 0.0
    gap_pct = ((guardian_price - competitor_price) / guardian_price) * 100 if guardian_price else 0.0

    return {
        "current_margin_pct": round(current_margin, 2),
        "margin_if_matched_pct": round(margin_if_matched, 2),
        "price_gap_pct": round(gap_pct, 2),
    }


def tool_propose_price_match(state: AgentState) -> Dict[str, Any]:
    return {
        "old_price": state["guardian_price"],
        "new_price": state["competitor_price"],
        "target_margin_pct": round(state["target_margin"], 2),
        "competitor_name": state["competitor_name"],
    }


def tool_lookup_supplier_policy(state: AgentState) -> Dict[str, Any]:
    brand_name = state["brand_name"] or state["competitor_name"]
    context = query_supplier_policy_rag(brand_name, "Summarize cost protection policy for this undercutting case.")
    return {
        "brand_name": brand_name,
        "policy_context": context,
    }


def tool_generate_supplier_email(state: AgentState) -> Dict[str, Any]:
    subject = "[Cost Protection Request] Margin defense for competitor undercutting"
    body = (
        f"Dear supplier team,\n\n"
        f"Guardian detected a major price gap on product ID {state['product_id']}.\n"
        f"Competitor {state['competitor_name']} is currently at {state['competitor_price']:,.0f} VND.\n"
        f"Our current cost is {state['cost_price']:,.0f} VND and matching that price would reduce margin below the safety threshold.\n\n"
        f"Supplier policy context:\n{state['negotiation_context']}\n\n"
        f"Please review a temporary cost-protection mechanism so we can defend market share without margin leakage.\n\n"
        f"Regards,\nGuardian Category Management"
    )
    return {
        "recipient": "partner@beautybrands.com",
        "subject": subject,
        "body": body,
    }


def build_alert_decision_context(db: Session, alert: models.Alert) -> Dict[str, Any]:
    product = alert.product
    if not product:
        return {"status": "skipped", "reason": "missing_product"}

    latest_price = (
        db.query(models.CompetitorPrice)
        .filter(
            models.CompetitorPrice.product_id == product.id,
            models.CompetitorPrice.stock_status != "OUT_OF_STOCK",
            models.CompetitorPrice.net_price.isnot(None),
            models.CompetitorPrice.is_suspicious == False,
        )
        .order_by(models.CompetitorPrice.scraped_at.desc())
        .first()
    )

    if not latest_price:
        return {"status": "skipped", "reason": "missing_competitor_price"}

    cfg = get_agent_config()
    min_margin_pct = cfg.get("min_margin", 0.15) * 100.0
    current_margin_pct = ((product.guardian_price - product.cost_price) / product.guardian_price) * 100 if product.guardian_price else 0.0
    margin_if_matched_pct = ((latest_price.net_price - product.cost_price) / latest_price.net_price) * 100 if latest_price.net_price else 0.0
    price_gap_pct = ((product.guardian_price - latest_price.net_price) / product.guardian_price) * 100 if product.guardian_price else 0.0

    if margin_if_matched_pct >= min_margin_pct:
        strategy = "match"
        recommended_action = "Approve price match"
        rationale = (
            f"Competitor {latest_price.competitor_name} is cheaper by {price_gap_pct:.1f}% and margin after matching "
            f"remains {margin_if_matched_pct:.1f}% above the floor of {min_margin_pct:.1f}%."
        )
    else:
        strategy = "negotiate"
        recommended_action = "Draft supplier protection request"
        rationale = (
            f"Matching {latest_price.competitor_name} would drop margin to {margin_if_matched_pct:.1f}%, "
            f"below the floor of {min_margin_pct:.1f}%, so the safer move is supplier negotiation."
        )

    return {
        "status": "ready",
        "alert_id": alert.id,
        "product_id": product.id,
        "product_name": product.name,
        "category": product.category,
        "guardian_price": round(product.guardian_price, 2),
        "cost_price": round(product.cost_price, 2),
        "current_margin_pct": round(current_margin_pct, 2),
        "competitor_name": latest_price.competitor_name,
        "competitor_price": round(latest_price.net_price, 2),
        "price_gap_pct": round(price_gap_pct, 2),
        "margin_if_matched_pct": round(margin_if_matched_pct, 2),
        "strategy": strategy,
        "recommended_action": recommended_action,
        "rationale": rationale,
        "severity": alert.severity,
        "message": alert.message,
        "channel_url": latest_price.url,
        "scraped_at": latest_price.scraped_at.isoformat() if latest_price.scraped_at else None,
    }


def node_run_margin_analysis(state: AgentState) -> AgentState:
    metrics = _run_agent_tool(
        state,
        "compute_margin_scenarios",
        {
            "product_id": state["product_id"],
            "guardian_price": state["guardian_price"],
            "competitor_price": state["competitor_price"],
            "cost_price": state["cost_price"],
        },
        lambda: tool_compute_margin_scenarios(state),
    )

    state["target_margin"] = metrics["margin_if_matched_pct"]
    _append_log(
        state,
        (
            f"  Guardian {state['guardian_price']:,.0f} VND | Cost {state['cost_price']:,.0f} VND | "
            f"Competitor {state['competitor_price']:,.0f} VND"
        ),
    )
    _append_log(
        state,
        (
            f"  Current margin {metrics['current_margin_pct']:.1f}% | "
            f"Margin if matched {metrics['margin_if_matched_pct']:.1f}% | "
            f"Gap {metrics['price_gap_pct']:.1f}%"
        ),
    )
    return state


def node_determine_strategy(state: AgentState) -> AgentState:
    _append_log(state, f"[{_timestamp()}] [Node: determine_strategy] Selecting strategy")
    cfg = get_agent_config()
    min_margin_pct = cfg.get("min_margin", 0.15) * 100.0
    custom_instruction = cfg.get("custom_instruction", "")
    openai_key = os.getenv("OPENAI_API_KEY", "")
    target_margin = state["target_margin"]

    if not openai_key or "your_openai" in openai_key:
        _append_log(state, "  [Fallback] OPENAI_API_KEY is not configured. Using rules.")
        strategy = "match" if target_margin >= min_margin_pct else "negotiate"
        reason = (
            f"Rule-based decision with target margin {target_margin:.1f}% "
            f"and floor {min_margin_pct:.1f}%."
        )
    else:
        try:
            from langchain.schema import HumanMessage, SystemMessage
            from langchain_openai import ChatOpenAI

            callbacks = []
            langfuse_callback = get_langfuse_callback()
            if langfuse_callback:
                callbacks.append(langfuse_callback)
                _append_log(state, "  [Tracing] Langfuse callback attached to LLM call.")

            llm = ChatOpenAI(
                model="gpt-4o-mini",
                api_key=openai_key,
                temperature=0.0,
                request_timeout=8.0,
            )

            system_prompt = (
                "You are the pricing decision engine for Guardian.\n"
                f"If target_margin >= {min_margin_pct:.1f}%, return strategy 'match'.\n"
                f"If target_margin < {min_margin_pct:.1f}%, return strategy 'negotiate'.\n"
                f"Custom instruction: {custom_instruction}\n"
                'Return JSON only: {"strategy":"match|negotiate","reasoning":"..."}'
            )
            prompt = (
                f"Product {state['product_id']}, competitor {state['competitor_name']}, "
                f"target_margin={target_margin:.1f}%."
            )

            response = llm.invoke(
                [SystemMessage(content=system_prompt), HumanMessage(content=prompt)],
                config={"callbacks": callbacks} if callbacks else {},
            )

            content = response.content.strip()
            if content.startswith("```"):
                import re

                content = re.sub(r"^```(?:json)?\n|```$", "", content, flags=re.MULTILINE).strip()

            parsed = json.loads(content)
            strategy = parsed.get("strategy", "negotiate")
            reason = parsed.get("reasoning", "No reasoning returned.")
        except Exception as exc:
            _append_log(state, f"  [Warning] LLM strategy call failed: {exc}. Falling back to rules.")
            strategy = "match" if target_margin >= min_margin_pct else "negotiate"
            reason = f"Fallback decision after LLM error. target_margin={target_margin:.1f}%."

    state["strategy"] = strategy
    _append_log(state, f"  [Decision] {strategy.upper()} | {reason}")
    return state


def node_apply_auto_match(state: AgentState) -> AgentState:
    proposal = _run_agent_tool(
        state,
        "adjust_system_price",
        {
            "product_id": state["product_id"],
            "guardian_price": state["guardian_price"],
            "competitor_price": state["competitor_price"],
        },
        lambda: tool_propose_price_match(state),
    )

    actions = list(state.get("actions_created", []))
    actions.append(
        {
            "action_type": "AUTO_PRICE_MATCH",
            "description": (
                f"Propose matching Guardian price with {state['competitor_name']} from "
                f"{state['guardian_price']:,.0f} to {state['competitor_price']:,.0f} VND."
            ),
            "data": json.dumps(proposal),
        }
    )
    state["actions_created"] = actions
    _append_log(state, f"  [Action] Price-match proposal created for {state['competitor_name']}.")
    return state


def node_draft_supplier_negotiation(state: AgentState) -> AgentState:
    policy_result = _run_agent_tool(
        state,
        "query_supplier_policy",
        {
            "product_id": state["product_id"],
            "brand_name": state["brand_name"],
            "competitor_name": state["competitor_name"],
        },
        lambda: tool_lookup_supplier_policy(state),
    )
    state["negotiation_context"] = policy_result["policy_context"]

    email_result = _run_agent_tool(
        state,
        "generate_supplier_negotiation_draft",
        {
            "product_id": state["product_id"],
            "competitor_price": state["competitor_price"],
        },
        lambda: tool_generate_supplier_email(state),
    )

    state["email_draft"] = email_result
    actions = list(state.get("actions_created", []))
    actions.append(
        {
            "action_type": "SUPPLIER_EMAIL_DRAFT",
            "description": "Generated a supplier cost-protection draft to defend margin.",
            "data": json.dumps(
                {
                    **email_result,
                    "competitor_price": state["competitor_price"],
                    "rag_context": state["negotiation_context"],
                }
            ),
        }
    )
    state["actions_created"] = actions
    _append_log(state, "  [Action] Supplier negotiation draft created.")
    return state


def run_langgraph_agent_for_alert(db: Session, alert: models.Alert) -> Dict[str, Any]:
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
        negotiation_context="",
        email_draft={},
        logs=[f"[LangGraph Agent Starting] Optimizing alert ID {alert.id}"],
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
            result = _execute_agent_graph(initial_state)
            span.update(
                output={
                    "strategy": result.get("strategy"),
                    "tool_events": len(result.get("tool_events", [])),
                    "actions_created": len(result.get("actions_created", [])),
                }
            )
            return result

    return _execute_agent_graph(initial_state)


def _execute_agent_graph(initial_state: AgentState) -> Dict[str, Any]:
    try:
        from langgraph.graph import END, StateGraph

        workflow = StateGraph(AgentState)
        workflow.add_node("margin_analysis", node_run_margin_analysis)
        workflow.add_node("determine_strategy", node_determine_strategy)
        workflow.add_node("apply_auto_match", node_apply_auto_match)
        workflow.add_node("supplier_negotiation", node_draft_supplier_negotiation)
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
        state = node_run_margin_analysis(initial_state)
        state = node_determine_strategy(state)
        if state["strategy"] == "match":
            state = node_apply_auto_match(state)
        else:
            state = node_draft_supplier_negotiation(state)
        return state


def run_agentic_optimization_loop(
    db: Session,
    task_id: Optional[int] = None,
    refresh_market_data: bool = True,
    max_alerts: int = 6,
) -> models.AgentTask:
    task = None
    if task_id is not None:
        task = db.query(models.AgentTask).filter(models.AgentTask.id == task_id).first()

    if not task:
        task = models.AgentTask(
            objective="Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index.",
            status="Running",
            logs="[Agent Initialized] Starting autonomous pricing watchtower...\n",
        )
        db.add(task)
        db.commit()
        db.refresh(task)
    else:
        task.objective = "Autonomously scan competitor channels, refresh pricing intelligence, protect margins, and optimize competitor index."
        task.status = "Running"
        task.logs = "[Agent Initialized] Starting autonomous pricing watchtower...\n"
        task.completed_at = None
        db.commit()
        db.refresh(task)

    logs = [f"[Agent Task ID {task.id}] Objective: {task.objective}"]
    langfuse = get_langfuse_client()

    def _run_loop():
        if refresh_market_data:
            logs.append("[Perceive] Refreshing competitor prices across tracked channels...")
            task.logs = "\n".join(logs)
            db.commit()
            scrape_results = run_scraper_for_all_products(db)
            item_count = sum(len(result or []) for result in scrape_results.values())
            logs.append(
                f"[Perceive Complete] Scraper refreshed {len(scrape_results)} products and recorded {item_count} channel observations."
            )
            task.logs = "\n".join(logs)
            db.commit()
        else:
            logs.append("[Perceive] Skipped live refresh. Using latest stored competitor data.")
            task.logs = "\n".join(logs)
            db.commit()

        alerts = db.query(models.Alert).filter(models.Alert.is_resolved == False).all()
        logs.append(f"[Reason] Detected {len(alerts)} unresolved alerts after refresh.")
        task.logs = "\n".join(logs)
        db.commit()

        if not alerts:
            logs.append("No active alerts. System remains stable.")
            task.status = "Completed"
            task.completed_at = datetime.utcnow()
            task.logs = "\n".join(logs)
            db.commit()
            return task

        for alert in alerts[:max_alerts]:
            agent_result = run_langgraph_agent_for_alert(db, alert)
            for agent_log in agent_result.get("logs", []):
                logs.append(f"  {agent_log}")

            for act in agent_result.get("actions_created", []):
                action_record = models.AgentAction(
                    task_id=task.id,
                    product_id=alert.product_id,
                    action_type=act["action_type"],
                    description=act["description"],
                    status="Pending" if act["action_type"] == "AUTO_PRICE_MATCH" else "Executed",
                    data=act["data"],
                )
                db.add(action_record)

            db.commit()
            task.logs = "\n".join(logs)
            db.commit()

        task.status = "Completed"
        logs.append("[Act Complete] All selected alerts were processed through the pricing workflow.")
        task.completed_at = datetime.utcnow()
        task.logs = "\n".join(logs)
        db.commit()
        return task

    try:
        if langfuse:
            with langfuse.start_as_current_observation(
                as_type="span",
                name="pricing-agent-run",
                input={"task_id": task.id, "objective": task.objective},
            ) as root_span:
                result = _run_loop()
                root_span.update(
                    output={
                        "status": result.status,
                        "completed_at": result.completed_at.isoformat() if result.completed_at else None,
                    }
                )
                return result

        return _run_loop()
    except Exception as exc:
        logs.append(f"[CRITICAL ERROR] {exc}")
        task.status = "Failed"
        task.completed_at = datetime.utcnow()
        task.logs = "\n".join(logs)
        db.commit()
        return task
