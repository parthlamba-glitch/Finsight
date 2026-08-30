"""
FinSight Fake Financial Engine (Mock)
====================================
Temporary mock financial engine for testing the AI pipeline:
    intent_router -> engine -> explainer

IMPORTANT:
This is NOT the real financial engine. All functions return realistic,
deterministic mock data matching the expected future engine schema.
No database or external dependencies required.
"""

from datetime import date
import json
from typing import Any, Dict, List, Optional


def get_balance(
    user_id: str = "demo_user",
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Mock fetch of current account balances and total net worth.
    """
    return {
        "balance": 42000,
        "as_of": date.today().isoformat(),
    }


def get_spending_summary(
    user_id: str = "demo_user",
    period: str = "this_month",
    category: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Mock retrieval of spending breakdown and totals over a given time period.
    """
    by_category = {
        "Food": 8000,
        "Transport": 3000,
    }

    if category:
        cat_formatted = category.strip().capitalize()
        cat_amount = by_category.get(cat_formatted, 4000)
        return {
            "total": cat_amount,
            "period": period,
            "by_category": {cat_formatted: cat_amount},
            "vs_last_period_pct": 15,
        }

    return {
        "total": 25000,
        "period": period,
        "by_category": by_category,
        "vs_last_period_pct": 15,
    }


def check_affordability(
    user_id: str = "demo_user",
    amount: float = 0.0,
    item_description: Optional[str] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Mock evaluation of whether user can afford a specific purchase amount.
    """
    current_balance = 42000
    upcoming_bills = 5000
    safe_balance = current_balance - upcoming_bills  # 37000

    can_afford = amount <= safe_balance
    balance_after = current_balance - int(amount) if can_afford else current_balance

    if can_afford:
        reasoning = ["Purchase leaves sufficient balance"]
    else:
        reasoning = ["Purchase exceeds safe discretionary balance after upcoming bills"]

    return {
        "can_afford": can_afford,
        "balance_after": balance_after,
        "upcoming_bills": upcoming_bills,
        "reasoning_facts": reasoning,
    }


def project_goal_completion(
    user_id: str = "demo_user",
    goal_id: str = "goal_efund_001",
    hypothetical_contribution: Optional[float] = None,
    **kwargs: Any,
) -> Dict[str, Any]:
    """
    Mock estimation of target completion date and progress for a savings goal.
    """
    current_months = 6
    if hypothetical_contribution and hypothetical_contribution > 0:
        hypothetical_months = max(1, current_months - 2)
    else:
        hypothetical_months = current_months

    return {
        "goal_name": "Emergency Fund",
        "current_months_remaining": current_months,
        "hypothetical_months_remaining": hypothetical_months,
    }


def get_insights(
    user_id: str = "demo_user",
    **kwargs: Any,
) -> List[Dict[str, Any]]:
    """
    Mock retrieval of AI financial insights, spending anomalies, and recurring trends.
    """
    return [
        {
            "type": "spending_increase",
            "category": "Food",
            "percentage": 22,
            "period": "3 months",
        }
    ]
