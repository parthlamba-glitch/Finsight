"""
Deterministic Financial Engine for FinSight.

ARCHITECTURAL PRINCIPLES:
-------------------------
1. Absolute Separation of Math and Language:
   - ZERO LLM logic: No OpenAI, Gemini, prompt building, or natural-language generation.
   - All computation is performed deterministically using Decimal precision.
2. Authoritative Balance:
   - Authoritative balance is defined strictly as SUM(transaction.amount) across user-owned accounts.
   - accounts.balance is NEVER used for financial calculations.
3. Money Sign Convention:
   - Positive (+) = Money entering account (Income, Opening Balance, Refund).
   - Negative (-) = Money leaving account (Expenses, Purchases, Bills).
4. Pure Determinism:
   - No datetime.now() or datetime.utcnow() for time period anchoring.
   - Analysis periods are anchored deterministically to the user's latest transaction date (as_of).
5. Database Ownership:
   - Transactions are strictly verified via the Account -> User ownership path.
"""

from decimal import Decimal, ROUND_CEILING, ROUND_HALF_UP
from datetime import datetime, date, timedelta
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Goal, Bill

ALL_CATEGORIES: List[str] = [
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
]


def get_balance(user_id: int, db: Session) -> Dict[str, Any]:
    """
    Calculates the authoritative user balance from transaction history.

    Authoritative balance = SUM(transaction.amount) for all transactions
    belonging to the user's accounts.

    Args:
        user_id: The ID of the user.
        db: SQLAlchemy database session.

    Returns:
        Dict:
        {
            "balance": Decimal,
            "as_of": datetime | None
        }

    Raises:
        ValueError: If user does not exist.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    transactions = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Account.user_id == user_id, Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    if not transactions:
        return {
            "balance": Decimal("0.00"),
            "as_of": None,
        }

    authoritative_balance = sum((t.amount for t in transactions), Decimal("0.00"))
    latest_tx_date = max(t.transaction_date for t in transactions)

    return {
        "balance": authoritative_balance,
        "as_of": latest_tx_date,
    }


def _get_previous_calendar_month(year: int, month: int) -> Tuple[int, int]:
    """Returns the (year, month) immediately preceding the given calendar month."""
    if month == 1:
        return (year - 1, 12)
    return (year, month - 1)


def get_spending_summary(
    user_id: int,
    db: Session,
    period: str = "this_month"
) -> Dict[str, Any]:
    """
    Computes deterministic category spending totals and percentage change against
    the previous calendar month.

    - "this_month": calendar month containing the user's latest transaction (day 1 through latest tx).
    - "last_month": complete calendar month immediately preceding that month.

    Args:
        user_id: The ID of the user.
        db: SQLAlchemy database session.
        period: "this_month" or "last_month".

    Returns:
        Dict:
        {
            "total": Decimal,
            "by_category": Dict[str, Decimal],
            "vs_last_period_pct": Dict[str, Decimal]
        }

    Raises:
        ValueError: If user does not exist or period is unsupported.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    if period not in ("this_month", "last_month"):
        raise ValueError(f"Unsupported period '{period}'. Supported periods are: 'this_month', 'last_month'.")

    transactions = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Account.user_id == user_id, Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    by_category: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in ALL_CATEGORIES}
    vs_last_period_pct: Dict[str, Decimal] = {cat: Decimal("0.00") for cat in ALL_CATEGORIES}
    vs_last_period_pct["total"] = Decimal("0.00")

    if not transactions:
        return {
            "total": Decimal("0.00"),
            "by_category": by_category,
            "vs_last_period_pct": vs_last_period_pct,
        }

    as_of = max(t.transaction_date for t in transactions)

    # Determine current and previous calendar periods
    if period == "this_month":
        curr_year, curr_month = as_of.year, as_of.month
        prev_year, prev_month = _get_previous_calendar_month(curr_year, curr_month)
    else:  # "last_month"
        curr_year, curr_month = _get_previous_calendar_month(as_of.year, as_of.month)
        prev_year, prev_month = _get_previous_calendar_month(curr_year, curr_month)

    # Filter negative amounts as spending (converted to positive Decimal values)
    curr_expenses = [
        t for t in transactions
        if t.amount < Decimal("0.00")
        and t.transaction_date.year == curr_year
        and t.transaction_date.month == curr_month
    ]

    prev_expenses = [
        t for t in transactions
        if t.amount < Decimal("0.00")
        and t.transaction_date.year == prev_year
        and t.transaction_date.month == prev_month
    ]

    for cat in ALL_CATEGORIES:
        cat_curr = sum((abs(t.amount) for t in curr_expenses if t.category == cat), Decimal("0.00"))
        cat_prev = sum((abs(t.amount) for t in prev_expenses if t.category == cat), Decimal("0.00"))

        by_category[cat] = cat_curr

        if cat_prev > Decimal("0.00"):
            pct = (((cat_curr - cat_prev) / cat_prev) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        else:
            pct = Decimal("0.00")

        vs_last_period_pct[cat] = pct

    total_curr = sum((abs(t.amount) for t in curr_expenses), Decimal("0.00"))
    total_prev = sum((abs(t.amount) for t in prev_expenses), Decimal("0.00"))

    if total_prev > Decimal("0.00"):
        total_pct = (((total_curr - total_prev) / total_prev) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    else:
        total_pct = Decimal("0.00")

    vs_last_period_pct["total"] = total_pct

    return {
        "total": total_curr,
        "by_category": by_category,
        "vs_last_period_pct": vs_last_period_pct,
    }


def check_affordability(
    user_id: int,
    amount: Decimal,
    db: Session
) -> Dict[str, Any]:
    """
    Deterministically evaluates whether a user can afford an expense of `amount`,
    factoring in authoritative balance, upcoming unpaid bills within 30 days, and active goals.

    Args:
        user_id: The ID of the user.
        amount: The proposed purchase amount (positive Decimal).
        db: SQLAlchemy database session.

    Returns:
        Dict:
        {
            "can_afford": bool,
            "balance_after": Decimal,
            "upcoming_bills": Decimal,
            "savings_goal_impact_months": Decimal,
            "reasoning_facts": list
        }

    Raises:
        ValueError: If user does not exist or amount is non-positive.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    if amount <= Decimal("0.00"):
        raise ValueError(f"Purchase amount must be positive, got {amount}.")

    balance_info = get_balance(user_id, db)
    current_balance: Decimal = balance_info["balance"]
    as_of_dt: Optional[datetime] = balance_info["as_of"]
    as_of_date = as_of_dt.date() if as_of_dt else date(2026, 8, 27)

    # Upcoming unpaid bills due in [as_of_date, as_of_date + 30 days]
    upcoming_bills_query = (
        db.query(Bill)
        .filter(
            Bill.user_id == user_id,
            Bill.status == "unpaid",
            Bill.due_date >= as_of_date,
            Bill.due_date <= as_of_date + timedelta(days=30),
        )
        .all()
    )
    upcoming_bills = sum((b.amount for b in upcoming_bills_query), Decimal("0.00"))

    balance_after = current_balance - amount
    available_after_bills_and_purchase = current_balance - upcoming_bills - amount
    can_afford = (available_after_bills_and_purchase >= Decimal("0.00"))

    # Active savings goals impact
    active_goals = (
        db.query(Goal)
        .filter(Goal.user_id == user_id, Goal.status == "active")
        .order_by(Goal.id.asc())
        .all()
    )

    goal_impact_months_list: List[Decimal] = []
    goal_facts: List[Dict[str, Any]] = []

    for g in active_goals:
        if g.monthly_contribution > Decimal("0.00"):
            impact_months = (amount / g.monthly_contribution).to_integral_value(rounding=ROUND_CEILING)
            goal_impact_months_list.append(impact_months)
            goal_facts.append({
                "fact": "goal_impact",
                "goal_id": g.id,
                "goal_name": g.name,
                "monthly_contribution": f"{g.monthly_contribution:.2f}",
                "impact_months": str(impact_months),
            })

    savings_goal_impact_months = max(goal_impact_months_list) if goal_impact_months_list else Decimal("0")

    reasoning_facts: List[Dict[str, Any]] = [
        {"fact": "current_balance", "value": f"{current_balance:.2f}"},
        {"fact": "purchase_amount", "value": f"{amount:.2f}"},
        {"fact": "upcoming_bills", "value": f"{upcoming_bills:.2f}"},
        {"fact": "balance_after_purchase", "value": f"{balance_after:.2f}"},
        {"fact": "available_after_bills_and_purchase", "value": f"{available_after_bills_and_purchase:.2f}"},
    ]
    reasoning_facts.extend(goal_facts)

    return {
        "can_afford": can_afford,
        "balance_after": balance_after,
        "upcoming_bills": upcoming_bills,
        "savings_goal_impact_months": savings_goal_impact_months,
        "reasoning_facts": reasoning_facts,
    }


def project_goal_completion(
    goal_id: int,
    db: Session,
    hypothetical_contribution: Optional[Decimal] = None
) -> Dict[str, Any]:
    """
    Calculates deterministic goal projection and estimated completion timeline
    using exact Decimal math.

    Args:
        goal_id: The ID of the goal.
        db: SQLAlchemy database session.
        hypothetical_contribution: Optional override for monthly contribution simulation.

    Returns:
        Dict:
        {
            "current_months_remaining": Decimal,
            "hypothetical_months_remaining": Decimal | None
        }

    Raises:
        ValueError: If goal does not exist, monthly_contribution <= 0, or hypothetical <= 0.
    """
    goal = db.query(Goal).filter(Goal.id == goal_id).first()
    if not goal:
        raise ValueError(f"Goal with id {goal_id} does not exist.")

    if goal.status == "completed" or (goal.target_amount - goal.current_amount) <= Decimal("0.00"):
        hypo_val = Decimal("0") if hypothetical_contribution is not None else None
        return {
            "current_months_remaining": Decimal("0"),
            "hypothetical_months_remaining": hypo_val,
        }

    remaining = goal.target_amount - goal.current_amount

    if goal.monthly_contribution <= Decimal("0.00"):
        raise ValueError("Goal monthly contribution must be greater than zero.")

    current_months = (remaining / goal.monthly_contribution).to_integral_value(rounding=ROUND_CEILING)

    if hypothetical_contribution is not None:
        if not isinstance(hypothetical_contribution, Decimal):
            hypothetical_contribution = Decimal(str(hypothetical_contribution))
        if hypothetical_contribution <= Decimal("0.00"):
            raise ValueError("Hypothetical contribution must be greater than zero.")
        hypothetical_months = (remaining / hypothetical_contribution).to_integral_value(rounding=ROUND_CEILING)
    else:
        hypothetical_months = None

    return {
        "current_months_remaining": current_months,
        "hypothetical_months_remaining": hypothetical_months,
    }


def get_insights(user_id: int, db: Session) -> List[Dict[str, Any]]:
    """
    Generates a list of deterministic structured financial insights:
    - Category spending spikes (>= 10% increase vs last month)
    - Generic subscription increases (recurring merchant price increases across consecutive months)
    - Upcoming bill alerts (due within 7 days)

    Args:
        user_id: The ID of the user.
        db: SQLAlchemy database session.

    Returns:
        List of structured insight dicts. Zero natural language or LLM narration.

    Raises:
        ValueError: If user does not exist.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    transactions = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(Account.user_id == user_id, Transaction.user_id == user_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )

    if not transactions:
        return []

    as_of = max(t.transaction_date for t in transactions)
    as_of_date = as_of.date()

    insights: List[Dict[str, Any]] = []

    # 1. Category Spending Increase (>= 10%)
    spending_summary = get_spending_summary(user_id, db, period="this_month")
    for cat, pct in spending_summary["vs_last_period_pct"].items():
        if cat != "total" and pct >= Decimal("10.00") and spending_summary["by_category"].get(cat, Decimal("0.00")) > Decimal("0.00"):
            insights.append({
                "type": "spending_increase",
                "category": cat,
                "pct": pct,
                "period": "this_month",
            })

    # 2. Generic Subscription Price Increase Detection
    # Group expense transactions by merchant and calendar month (year, month)
    merchant_monthly_txs: Dict[str, Dict[Tuple[int, int], List[Transaction]]] = {}
    for t in transactions:
        if t.merchant_name and t.amount < Decimal("0.00"):
            m_key = t.merchant_name.strip()
            if m_key not in merchant_monthly_txs:
                merchant_monthly_txs[m_key] = {}
            period_key = (t.transaction_date.year, t.transaction_date.month)
            if period_key not in merchant_monthly_txs[m_key]:
                merchant_monthly_txs[m_key][period_key] = []
            merchant_monthly_txs[m_key][period_key].append(t)

    for merchant, month_dict in merchant_monthly_txs.items():
        sorted_periods = sorted(month_dict.keys())
        for i in range(1, len(sorted_periods)):
            p_prev = sorted_periods[i - 1]
            p_curr = sorted_periods[i]

            # Check if periods are consecutive calendar months
            expected_curr = (p_prev[0], p_prev[1] + 1) if p_prev[1] < 12 else (p_prev[0] + 1, 1)
            if p_curr == expected_curr:
                prev_txs = month_dict[p_prev]
                curr_txs = month_dict[p_curr]

                # Subscriptions have 1 recurring payment per month
                if len(prev_txs) == 1 and len(curr_txs) == 1:
                    prev_tx = prev_txs[0]
                    curr_tx = curr_txs[0]
                    prev_amt = abs(prev_tx.amount)
                    curr_amt = abs(curr_tx.amount)

                    # Identify subscriptions generically: Entertainment category, or description indicating subscription/membership/plan
                    is_subscription = (
                        curr_tx.category == "Entertainment"
                        or "subscription" in (curr_tx.description or "").lower()
                        or "membership" in (curr_tx.description or "").lower()
                    )

                    if is_subscription and curr_amt > prev_amt and prev_amt > Decimal("0.00"):
                        pct = (((curr_amt - prev_amt) / prev_amt) * Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                        period_str = datetime(p_curr[0], p_curr[1], 1).strftime("%B %Y")
                        insights.append({
                            "type": "subscription_increase",
                            "category": curr_tx.category,
                            "merchant": merchant,
                            "pct": pct,
                            "period": period_str,
                        })

    # 3. Upcoming Bill Alert (due within 7 days of as_of_date)
    upcoming_soon = (
        db.query(Bill)
        .filter(
            Bill.user_id == user_id,
            Bill.status == "unpaid",
            Bill.due_date >= as_of_date,
            Bill.due_date <= as_of_date + timedelta(days=7),
        )
        .order_by(Bill.due_date.asc())
        .all()
    )

    for b in upcoming_soon:
        insights.append({
            "type": "upcoming_bill",
            "category": b.category,
            "amount": b.amount,
            "period": "within_7_days",
        })

    return insights
