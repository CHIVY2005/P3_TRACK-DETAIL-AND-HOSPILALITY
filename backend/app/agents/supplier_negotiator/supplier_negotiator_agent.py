from typing import Any, MutableMapping

from app.agents.shared.runtime_support import append_log, dumps_json, run_agent_tool
from app.agents.supplier_negotiator.supplier_negotiator_tools import generate_supplier_email, lookup_supplier_policy


def draft_supplier_negotiation(state: MutableMapping[str, Any]) -> MutableMapping[str, Any]:
    policy_result = run_agent_tool(
        state,
        "query_supplier_policy",
        {
            "product_id": state["product_id"],
            "brand_name": state["brand_name"],
            "competitor_name": state["competitor_name"],
        },
        lambda: lookup_supplier_policy(state),
    )
    state["negotiation_context"] = policy_result["policy_context"]

    email_result = run_agent_tool(
        state,
        "generate_supplier_negotiation_draft",
        {
            "product_id": state["product_id"],
            "competitor_price": state["competitor_price"],
        },
        lambda: generate_supplier_email(state),
    )

    state["email_draft"] = email_result
    actions = list(state.get("actions_created", []))
    actions.append(
        {
            "action_type": "SUPPLIER_EMAIL_DRAFT",
            "description": "Generated a supplier cost-protection draft to defend margin.",
            "data": dumps_json(
                {
                    **email_result,
                    "competitor_price": state["competitor_price"],
                    "policy_context": state["negotiation_context"],
                    "decision_summary": {
                        "strategy": state["strategy"],
                        "reason": state.get("decision_reason"),
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
    append_log(state, "  [Action] Initiated SupplierNegotiator tool. Successfully drafted a cost-protection email to partner@beautybrands.com defending our target margin.")
    return state
