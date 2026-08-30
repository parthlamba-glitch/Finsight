"""
Dashboard Router for FinSight.

Provides structured dashboard facts for the user interface and accessibility/AI narration layer.
Integrates with the deterministic financial engine for authoritative balances and spending summaries.
"""

from decimal import Decimal
from datetime import date, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models import User, Account, Goal, Bill
from backend.auth.dependencies import get_current_user
from backend.engine import get_balance, get_spending_summary
from backend.schemas import DashboardOverviewResponse, GoalResponse

router = APIRouter(tags=["Dashboard"])


@router.get("/overview", response_model=DashboardOverviewResponse, summary="Get Dashboard Overview")
@router.get("/api/v1/overview", response_model=DashboardOverviewResponse, include_in_schema=False)
@router.get("/api/v1/dashboard/overview", response_model=DashboardOverviewResponse, include_in_schema=False)
def get_dashboard_overview(
    user_id: Optional[int] = Query(None, description="Optional legacy demo user ID (overridden by authenticated JWT identity)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> DashboardOverviewResponse:
    """
    Returns structured dashboard overview facts for the authenticated user.
    """
    authoritative_user_id = current_user.id

    # 1. Authoritative balance and as_of date from deterministic engine
    balance_info = get_balance(authoritative_user_id, db)
    authoritative_balance: Decimal = balance_info["balance"]
    as_of = balance_info["as_of"]
    as_of_date = as_of.date() if as_of else date(2026, 8, 27)

    # 2. Monthly spending from deterministic engine
    spending_summary = get_spending_summary(authoritative_user_id, db, period="this_month")
    monthly_spending: Decimal = spending_summary["total"]

    # 3. Monthly income from active user accounts
    active_accounts = (
        db.query(Account)
        .filter(Account.user_id == authoritative_user_id, Account.is_active == True)
        .all()
    )
    monthly_income = sum((acc.monthly_income for acc in active_accounts), Decimal("0.00"))


    # 4. Authoritative Monthly Surplus & Compatibility Savings calculation
    monthly_surplus = monthly_income - monthly_spending
    savings = monthly_surplus  # Compatibility alias for cash-flow surplus

    # 5. Upcoming unpaid bills within 30-day window
    unpaid_bills = (
        db.query(Bill)
        .filter(
            Bill.user_id == authoritative_user_id,
            Bill.status == "unpaid",
            Bill.due_date >= as_of_date,
            Bill.due_date <= as_of_date + timedelta(days=30),
        )
        .all()
    )
    upcoming_bills_total = sum((b.amount for b in unpaid_bills), Decimal("0.00"))

    # 6. Active goals belonging to this user
    active_goals = (
        db.query(Goal)
        .filter(Goal.user_id == authoritative_user_id, Goal.status == "active")
        .order_by(Goal.id.asc())
        .all()
    )

    goals_responses = [GoalResponse.model_validate(g) for g in active_goals]

    return DashboardOverviewResponse(
        balance=authoritative_balance,
        monthly_income=monthly_income,
        monthly_spending=monthly_spending,
        savings=savings,
        monthly_surplus=monthly_surplus,
        upcoming_bills=upcoming_bills_total,
        goals=goals_responses,
    )
