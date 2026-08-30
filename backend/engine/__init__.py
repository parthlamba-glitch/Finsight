"""
FinSight Deterministic Financial Engine Package.
Exports public plain functions and insight fact helpers.
"""

from backend.engine.financial_engine import (
    get_balance,
    get_spending_summary,
    check_affordability,
    project_goal_completion,
    get_insights,
)
from backend.engine.insights import build_insight_fact

__all__ = [
    "get_balance",
    "get_spending_summary",
    "check_affordability",
    "project_goal_completion",
    "get_insights",
    "build_insight_fact",
]
