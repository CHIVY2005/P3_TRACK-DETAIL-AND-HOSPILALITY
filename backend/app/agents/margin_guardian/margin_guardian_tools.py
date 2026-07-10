from typing import Any, Dict, MutableMapping


def compute_margin_scenarios(state: MutableMapping[str, Any]) -> Dict[str, Any]:
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


def propose_price_match(state: MutableMapping[str, Any]) -> Dict[str, Any]:
    return {
        "old_price": state["guardian_price"],
        "new_price": state["competitor_price"],
        "target_margin_pct": round(state["target_margin"], 2),
        "competitor_name": state["competitor_name"],
    }
