from typing import Any, Dict, MutableMapping

def lookup_supplier_policy(state: MutableMapping[str, Any]) -> Dict[str, Any]:
    brand_name = state["brand_name"] or state["competitor_name"]
    context = build_supplier_policy_template(brand_name)
    return {
        "brand_name": brand_name,
        "policy_context": context,
    }


def generate_supplier_email(state: MutableMapping[str, Any]) -> Dict[str, Any]:
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


def build_supplier_policy_template(brand_name: str) -> str:
    normalized_brand = brand_name.lower()

    if "roche" in normalized_brand or "posay" in normalized_brand:
        return (
            "Rule-based policy: prioritize brand escalation for La Roche-Posay. "
            "Request temporary cost protection up to 20% and contact thao.nguyen@loreal.com."
        )

    if "bioderma" in normalized_brand:
        return (
            "Rule-based policy: request a 12,000 VND credit note per unit for Bioderma undercut cases. "
            "Primary contact: lam.hoang@minhanhbeauty.vn."
        )

    if "anessa" in normalized_brand or "shiseido" in normalized_brand:
        return (
            "Rule-based policy: route the case through Shiseido special discount approval within 48 hours. "
            "Primary contact: chi.linh@shiseido.com.vn."
        )

    return (
        f"Rule-based policy: competitor undercut detected for {brand_name}. "
        "Escalate to the supplier account manager and request temporary cost protection before matching price."
    )
