"""
Comprehensive Tests for FinSight Deterministic Financial Engine.

Covers:
- Database schema foundation and model constraints (preserved)
- get_balance(): Authoritative calculation, bypass Account.balance, Decimal precision, as_of date, edge cases
- get_spending_summary(): Categorical totals, percentages, this_month vs last_month, division by zero handling
- check_affordability(): Balance after, upcoming bills within 30 days, goal impacts, reasoning facts
- project_goal_completion(): Active projections, hypothetical contributions, completed goals, error handling
- get_insights(): Spending increases (>=10%), generic subscription increases, upcoming bill alerts
- Edge cases: Nonexistent entities, zero/negative inputs, empty transactions, mismatched ownership
"""

from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import List, Dict, Any
import pytest
from sqlalchemy.orm import Session

from backend.db import Base
from backend.models import (
    User,
    Account,
    Transaction,
    Goal,
    Bill,
    Document,
    VALID_TRANSACTION_TYPES,
    VALID_CATEGORIES,
    VALID_GOAL_STATUSES,
    VALID_BILL_STATUSES,
)
from backend.engine import (
    get_balance,
    get_spending_summary,
    check_affordability,
    project_goal_completion,
    get_insights,
    build_insight_fact,
)


class TestDatabaseFoundation:
    """Verifies table creation and schema integrity for all 6 models."""

    def test_all_six_tables_exist(self, db_session: Session):
        expected_tables = {"users", "accounts", "transactions", "goals", "bills", "documents"}
        actual_tables = set(Base.metadata.tables.keys())
        assert expected_tables.issubset(actual_tables), f"Missing tables: {expected_tables - actual_tables}"

    def test_user_creation_with_accessibility_prefs(self, db_session: Session):
        user = User(
            full_name="Aarav Sharma",
            email="aarav.test@example.com",
            accessibility_prefs={
                "voice_first": True,
                "screen_reader": True,
                "spoken_confirmations": True,
                "preferred_language": "en-IN",
            },
        )
        db_session.add(user)
        db_session.commit()

        queried = db_session.query(User).filter_by(email="aarav.test@example.com").first()
        assert queried is not None
        assert queried.accessibility_prefs["voice_first"] is True
        assert queried.accessibility_prefs["screen_reader"] is True
        assert queried.accessibility_prefs["preferred_language"] == "en-IN"

    def test_account_and_transaction_relationship_with_money_convention(self, db_session: Session):
        user = User(full_name="Priya Patel", email="priya.patel@example.com")
        db_session.add(user)
        db_session.flush()

        account = Account(
            user_id=user.id,
            name="Primary Checking",
            account_type="checking",
            balance=Decimal("25000.00"),
            monthly_income=Decimal("75000.00"),
            currency="INR",
        )
        db_session.add(account)
        db_session.flush()

        t_opening = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("25000.00"),
            currency="INR",
            transaction_type="income",
            category="Other",
            description="Opening Balance",
            transaction_date=datetime(2026, 5, 1, 9, 0),
        )
        t_expense = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("-620.00"),
            currency="INR",
            transaction_type="expense",
            category="Food",
            merchant_name="Swiggy",
            description="Dinner Delivery",
            transaction_date=datetime(2026, 5, 2, 20, 0),
        )

        db_session.add_all([t_opening, t_expense])
        db_session.commit()

        transactions = db_session.query(Transaction).filter_by(account_id=account.id).all()
        assert len(transactions) == 2
        total_authoritative_balance = sum(t.amount for t in transactions)
        assert total_authoritative_balance == Decimal("24380.00")

    def test_goal_model_constraints(self, db_session: Session):
        user = User(full_name="Rohan Gupta", email="rohan.gupta@example.com")
        db_session.add(user)
        db_session.flush()

        goal = Goal(
            user_id=user.id,
            name="Emergency Fund",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("30000.00"),
            monthly_contribution=Decimal("5000.00"),
            currency="INR",
            target_date=date(2026, 12, 31),
            status="active",
        )
        db_session.add(goal)
        db_session.commit()

        queried = db_session.query(Goal).filter_by(id=goal.id).first()
        assert queried is not None
        assert queried.target_amount == Decimal("100000.00")
        assert queried.status in VALID_GOAL_STATUSES

    def test_bill_model_constraints(self, db_session: Session):
        user = User(full_name="Sneha Rao", email="sneha.rao@example.com")
        db_session.add(user)
        db_session.flush()

        bill = Bill(
            user_id=user.id,
            name="Electricity Bill (BESCOM)",
            amount=Decimal("1850.00"),
            currency="INR",
            category="Bills",
            due_date=date(2026, 9, 5),
            frequency="monthly",
            status="unpaid",
            is_recurring=True,
        )
        db_session.add(bill)
        db_session.commit()

        queried = db_session.query(Bill).filter_by(id=bill.id).first()
        assert queried is not None
        assert queried.amount == Decimal("1850.00")
        assert queried.status == "unpaid"
        assert queried.status in VALID_BILL_STATUSES

    def test_document_model_storage(self, db_session: Session):
        user = User(full_name="Kavita Iyer", email="kavita.iyer@example.com")
        db_session.add(user)
        db_session.flush()

        doc = Document(
            user_id=user.id,
            filename="bescom_september_2026.pdf",
            file_path="/storage/documents/bescom_september_2026.pdf",
            document_type="bill",
            mime_type="application/pdf",
            raw_text="BESCOM Electricity Bill: Amount Due Rs 1850.00 Due Date: 05-09-2026",
            extracted_facts={"vendor": "BESCOM", "amount": 1850.00, "due_date": "2026-09-05"},
            is_suspicious=False,
        )
        db_session.add(doc)
        db_session.commit()

        queried = db_session.query(Document).filter_by(id=doc.id).first()
        assert queried is not None
        assert queried.document_type == "bill"
        assert queried.extracted_facts["amount"] == 1850.00

    def test_build_insight_fact_structure(self):
        fact = build_insight_fact(
            insight_type="spending_spike",
            severity="WARNING",
            category="Food",
            metric_name="monthly_food_spend",
            metric_value=Decimal("12500.00"),
            threshold_value=Decimal("8000.00"),
            metadata={"percentage_increase": 56.25},
        )
        assert fact["insight_type"] == "spending_spike"
        assert fact["severity"] == "WARNING"
        assert fact["metric_value"] == "12500.00"
        assert fact["threshold_value"] == "8000.00"
        assert fact["metadata"]["percentage_increase"] == 56.25


class TestGetBalance:
    """Verifies authoritative balance calculation, Decimal precision, as_of timestamp, and edge cases."""

    def test_authoritative_balance_calculated_from_transactions(self, db_session: Session):
        user = User(full_name="Test User", email="test.bal@example.com")
        db_session.add(user)
        db_session.flush()

        # Cached balance on account is intentionally wrong
        account = Account(
            user_id=user.id,
            name="Savings",
            account_type="savings",
            balance=Decimal("999999.99"),  # Cached balance should be ignored
            monthly_income=Decimal("50000.00"),
        )
        db_session.add(account)
        db_session.flush()

        tx1 = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("50000.00"),
            currency="INR",
            transaction_type="income",
            category="Other",
            description="Salary",
            transaction_date=datetime(2026, 8, 1, 9, 0),
        )
        tx2 = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("-15000.00"),
            currency="INR",
            transaction_type="expense",
            category="Bills",
            description="Rent",
            transaction_date=datetime(2026, 8, 5, 12, 0),
        )
        tx3 = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("-3250.75"),
            currency="INR",
            transaction_type="expense",
            category="Food",
            description="Groceries",
            transaction_date=datetime(2026, 8, 10, 18, 30),
        )
        db_session.add_all([tx1, tx2, tx3])
        db_session.commit()

        result = get_balance(user.id, db_session)
        assert isinstance(result["balance"], Decimal)
        assert result["balance"] == Decimal("31749.25")
        assert result["as_of"] == datetime(2026, 8, 10, 18, 30)

    def test_nonexistent_user_raises_value_error(self, db_session: Session):
        with pytest.raises(ValueError, match="does not exist"):
            get_balance(999999, db_session)

    def test_user_with_no_transactions_returns_zero(self, db_session: Session):
        user = User(full_name="Zero Tx User", email="zero.tx@example.com")
        db_session.add(user)
        db_session.commit()

        result = get_balance(user.id, db_session)
        assert result["balance"] == Decimal("0.00")
        assert result["as_of"] is None

    def test_mismatched_account_ownership_not_counted(self, db_session: Session):
        user1 = User(full_name="User One", email="user1@example.com")
        user2 = User(full_name="User Two", email="user2@example.com")
        db_session.add_all([user1, user2])
        db_session.flush()

        acc1 = Account(user_id=user1.id, name="Acc 1", balance=Decimal("0.00"))
        acc2 = Account(user_id=user2.id, name="Acc 2", balance=Decimal("0.00"))
        db_session.add_all([acc1, acc2])
        db_session.flush()

        # Valid transaction for user 1
        t1 = Transaction(
            account_id=acc1.id,
            user_id=user1.id,
            amount=Decimal("1000.00"),
            transaction_type="income",
            category="Other",
            transaction_date=datetime(2026, 8, 1),
        )
        # Transaction belonging to acc2 (user 2) but spoofing user_id=user1
        t2 = Transaction(
            account_id=acc2.id,
            user_id=user1.id,
            amount=Decimal("5000.00"),
            transaction_type="income",
            category="Other",
            transaction_date=datetime(2026, 8, 2),
        )
        db_session.add_all([t1, t2])
        db_session.commit()

        res1 = get_balance(user1.id, db_session)
        assert res1["balance"] == Decimal("1000.00")


class TestGetSpendingSummary:
    """Verifies categorical totals, month-over-month comparisons, and division by zero handling."""

    @pytest.fixture
    def spending_user(self, db_session: Session) -> User:
        user = User(full_name="Spending User", email="spending@example.com")
        db_session.add(user)
        db_session.flush()

        account = Account(user_id=user.id, name="Checking", balance=Decimal("0.00"))
        db_session.add(account)
        db_session.flush()

        # July 2026 transactions (Previous month)
        tx_july = [
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("75000.00"),  # Income: should NOT count as spending
                transaction_type="income",
                category="Other",
                transaction_date=datetime(2026, 7, 1, 9, 0),
            ),
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("-10000.00"),
                transaction_type="expense",
                category="Food",
                transaction_date=datetime(2026, 7, 5, 12, 0),
            ),
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("-5000.00"),
                transaction_type="expense",
                category="Bills",
                transaction_date=datetime(2026, 7, 10, 12, 0),
            ),
        ]

        # August 2026 transactions (This month, as_of: Aug 20)
        tx_aug = [
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("75000.00"),  # Income: should NOT count as spending
                transaction_type="income",
                category="Other",
                transaction_date=datetime(2026, 8, 1, 9, 0),
            ),
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("-12500.00"),  # Food: +25% increase from 10k
                transaction_type="expense",
                category="Food",
                transaction_date=datetime(2026, 8, 8, 14, 0),
            ),
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("-5000.00"),  # Bills: 0% change from 5k
                transaction_type="expense",
                category="Bills",
                transaction_date=datetime(2026, 8, 12, 10, 0),
            ),
            Transaction(
                account_id=account.id,
                user_id=user.id,
                amount=Decimal("-2000.00"),  # Transport: 0 in July -> +2000 (prev is 0 -> 0%)
                transaction_type="expense",
                category="Transport",
                transaction_date=datetime(2026, 8, 20, 18, 0),
            ),
        ]

        db_session.add_all(tx_july + tx_aug)
        db_session.commit()
        return user

    def test_spending_summary_this_month(self, db_session: Session, spending_user: User):
        summary = get_spending_summary(spending_user.id, db_session, period="this_month")

        assert summary["total"] == Decimal("19500.00")
        assert summary["by_category"]["Food"] == Decimal("12500.00")
        assert summary["by_category"]["Bills"] == Decimal("5000.00")
        assert summary["by_category"]["Transport"] == Decimal("2000.00")
        assert summary["by_category"]["Shopping"] == Decimal("0.00")

        # Sum of categories must equal total
        assert sum(summary["by_category"].values()) == summary["total"]

        # Food: ((12500 - 10000) / 10000) * 100 = 25.00%
        assert summary["vs_last_period_pct"]["Food"] == Decimal("25.00")
        # Bills: ((5000 - 5000) / 5000) * 100 = 0.00%
        assert summary["vs_last_period_pct"]["Bills"] == Decimal("0.00")
        # Transport: previous was 0 -> returns Decimal("0.00") without divide-by-zero
        assert summary["vs_last_period_pct"]["Transport"] == Decimal("0.00")
        # Total: ((19500 - 15000) / 15000) * 100 = 30.00%
        assert summary["vs_last_period_pct"]["total"] == Decimal("30.00")

    def test_spending_summary_last_month(self, db_session: Session, spending_user: User):
        summary = get_spending_summary(spending_user.id, db_session, period="last_month")
        # Last month = July 2026, compared to June 2026 (June has 0)
        assert summary["total"] == Decimal("15000.00")
        assert summary["by_category"]["Food"] == Decimal("10000.00")
        assert summary["by_category"]["Bills"] == Decimal("5000.00")

    def test_unsupported_period_raises_value_error(self, db_session: Session, spending_user: User):
        with pytest.raises(ValueError, match="Unsupported period"):
            get_spending_summary(spending_user.id, db_session, period="invalid_period")

    def test_nonexistent_user_raises_value_error(self, db_session: Session):
        with pytest.raises(ValueError, match="does not exist"):
            get_spending_summary(88888, db_session)


class TestCheckAffordability:
    """Verifies purchase affordability, 30-day upcoming bill consideration, and goal impact."""

    @pytest.fixture
    def afford_user(self, db_session: Session) -> User:
        user = User(full_name="Afford User", email="afford@example.com")
        db_session.add(user)
        db_session.flush()

        account = Account(user_id=user.id, name="Savings", balance=Decimal("0.00"))
        db_session.add(account)
        db_session.flush()

        # Balance: 50,000 INR
        tx = Transaction(
            account_id=account.id,
            user_id=user.id,
            amount=Decimal("50000.00"),
            transaction_type="income",
            category="Other",
            transaction_date=datetime(2026, 8, 20, 10, 0),
        )
        db_session.add(tx)

        # Active Goal: Monthly contribution = 10,000 INR
        goal = Goal(
            user_id=user.id,
            name="Emergency Fund",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("20000.00"),
            monthly_contribution=Decimal("10000.00"),
            status="active",
        )
        db_session.add(goal)

        # Unpaid Bill within 30 days: 6,000 INR (due 2026-09-05)
        bill1 = Bill(
            user_id=user.id,
            name="Electricity",
            amount=Decimal("6000.00"),
            category="Bills",
            due_date=date(2026, 9, 5),
            status="unpaid",
        )
        # Paid Bill: should NOT be counted in upcoming bills
        bill2 = Bill(
            user_id=user.id,
            name="Internet Paid",
            amount=Decimal("1500.00"),
            category="Bills",
            due_date=date(2026, 9, 1),
            status="paid",
        )
        # Bill beyond 30 days: should NOT be counted
        bill3 = Bill(
            user_id=user.id,
            name="Quarterly Tax",
            amount=Decimal("12000.00"),
            category="Bills",
            due_date=date(2026, 10, 15),
            status="unpaid",
        )

        db_session.add_all([bill1, bill2, bill3])
        db_session.commit()
        return user

    def test_clearly_affordable_purchase(self, db_session: Session, afford_user: User):
        # Balance: 50,000, Upcoming Bills: 6,000, Purchase: 10,000 -> Available after: 34,000
        res = check_affordability(afford_user.id, Decimal("10000.00"), db_session)
        assert res["can_afford"] is True
        assert res["balance_after"] == Decimal("40000.00")
        assert res["upcoming_bills"] == Decimal("6000.00")
        assert res["savings_goal_impact_months"] == Decimal("1")  # ceil(10000 / 10000) = 1
        assert len(res["reasoning_facts"]) >= 5

    def test_purchase_exceeding_balance(self, db_session: Session, afford_user: User):
        # Purchase: 60,000 > Balance 50,000
        res = check_affordability(afford_user.id, Decimal("60000.00"), db_session)
        assert res["can_afford"] is False
        assert res["balance_after"] == Decimal("-10000.00")
        assert res["savings_goal_impact_months"] == Decimal("6")  # ceil(60000 / 10000) = 6

    def test_purchase_unaffordable_due_to_upcoming_bills(self, db_session: Session, afford_user: User):
        # Balance: 50,000, Bills: 6,000, Purchase: 46,000 -> Available after: -2,000
        res = check_affordability(afford_user.id, Decimal("46000.00"), db_session)
        assert res["can_afford"] is False
        assert res["balance_after"] == Decimal("4000.00")

    def test_zero_or_negative_amount_raises_value_error(self, db_session: Session, afford_user: User):
        with pytest.raises(ValueError, match="positive"):
            check_affordability(afford_user.id, Decimal("0.00"), db_session)

        with pytest.raises(ValueError, match="positive"):
            check_affordability(afford_user.id, Decimal("-500.00"), db_session)


class TestProjectGoalCompletion:
    """Verifies deterministic goal projection, hypothetical simulations, and error handling."""

    def test_active_goal_projection(self, db_session: Session):
        user = User(full_name="Goal User", email="goal.user@example.com")
        db_session.add(user)
        db_session.flush()

        # Remaining: 150,000 - 45,000 = 105,000. Contribution: 10,000. Ceil(105000 / 10000) = 11 months.
        goal = Goal(
            user_id=user.id,
            name="Emergency Fund",
            target_amount=Decimal("150000.00"),
            current_amount=Decimal("45000.00"),
            monthly_contribution=Decimal("10000.00"),
            status="active",
        )
        db_session.add(goal)
        db_session.commit()

        # Normal projection
        res = project_goal_completion(goal.id, db_session)
        assert res["current_months_remaining"] == Decimal("11")
        assert res["hypothetical_months_remaining"] is None

        # Hypothetical higher contribution: 15,000 -> Ceil(105000 / 15000) = 7 months
        res_hypo_higher = project_goal_completion(goal.id, db_session, hypothetical_contribution=Decimal("15000.00"))
        assert res_hypo_higher["current_months_remaining"] == Decimal("11")
        assert res_hypo_higher["hypothetical_months_remaining"] == Decimal("7")

        # Hypothetical lower contribution: 5,000 -> Ceil(105000 / 5000) = 21 months
        res_hypo_lower = project_goal_completion(goal.id, db_session, hypothetical_contribution=Decimal("5000.00"))
        assert res_hypo_lower["hypothetical_months_remaining"] == Decimal("21")

    def test_completed_goal_returns_zero(self, db_session: Session):
        user = User(full_name="Goal User 2", email="goal.user2@example.com")
        db_session.add(user)
        db_session.flush()

        goal = Goal(
            user_id=user.id,
            name="New Laptop",
            target_amount=Decimal("80000.00"),
            current_amount=Decimal("80000.00"),
            monthly_contribution=Decimal("10000.00"),
            status="completed",
        )
        db_session.add(goal)
        db_session.commit()

        res = project_goal_completion(goal.id, db_session)
        assert res["current_months_remaining"] == Decimal("0")

    def test_invalid_contributions_raise_value_error(self, db_session: Session):
        user = User(full_name="Goal User 3", email="goal.user3@example.com")
        db_session.add(user)
        db_session.flush()

        goal = Goal(
            user_id=user.id,
            name="Car",
            target_amount=Decimal("500000.00"),
            current_amount=Decimal("50000.00"),
            monthly_contribution=Decimal("0.00"),
            status="active",
        )
        db_session.add(goal)
        db_session.commit()

        with pytest.raises(ValueError, match="greater than zero"):
            project_goal_completion(goal.id, db_session)

    def test_nonexistent_goal_raises_value_error(self, db_session: Session):
        with pytest.raises(ValueError, match="does not exist"):
            project_goal_completion(777777, db_session)


class TestGetInsights:
    """Verifies spending spikes, generic subscription price hike detection, and bill alerts."""

    def test_insights_detection(self, db_session: Session):
        user = User(full_name="Insight User", email="insight@example.com")
        db_session.add(user)
        db_session.flush()

        account = Account(user_id=user.id, name="Savings", balance=Decimal("0.00"))
        db_session.add(account)
        db_session.flush()

        # May: Netflix 499, Food 8000, Rent 25000
        # June: Netflix 499, Food 10000, Rent 25000
        # July: Netflix 699 (+40.08%), Food 12000, Rent 25000
        # August: Netflix 699, Food 15000 (+25%), Rent 25000
        txs = [
            # May
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-499.00"), transaction_type="expense", category="Entertainment", merchant_name="Netflix", transaction_date=datetime(2026, 5, 15)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-8000.00"), transaction_type="expense", category="Food", transaction_date=datetime(2026, 5, 20)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-25000.00"), transaction_type="expense", category="Bills", merchant_name="Landlord", transaction_date=datetime(2026, 5, 2)),
            # June
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-499.00"), transaction_type="expense", category="Entertainment", merchant_name="Netflix", transaction_date=datetime(2026, 6, 15)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-10000.00"), transaction_type="expense", category="Food", transaction_date=datetime(2026, 6, 20)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-25000.00"), transaction_type="expense", category="Bills", merchant_name="Landlord", transaction_date=datetime(2026, 6, 2)),
            # July (Netflix price increase 499 -> 699)
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-699.00"), transaction_type="expense", category="Entertainment", merchant_name="Netflix", transaction_date=datetime(2026, 7, 15)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-12000.00"), transaction_type="expense", category="Food", transaction_date=datetime(2026, 7, 20)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-25000.00"), transaction_type="expense", category="Bills", merchant_name="Landlord", transaction_date=datetime(2026, 7, 2)),
            # August (Food increase 12k -> 15k, as_of: Aug 25)
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-699.00"), transaction_type="expense", category="Entertainment", merchant_name="Netflix", transaction_date=datetime(2026, 8, 15)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-15000.00"), transaction_type="expense", category="Food", transaction_date=datetime(2026, 8, 20)),
            Transaction(account_id=account.id, user_id=user.id, amount=Decimal("-25000.00"), transaction_type="expense", category="Bills", merchant_name="Landlord", transaction_date=datetime(2026, 8, 25)),
        ]
        db_session.add_all(txs)

        # Upcoming bill due in 3 days (Aug 28 vs as_of Aug 25)
        bill_soon = Bill(
            user_id=user.id,
            name="Electricity Bill",
            amount=Decimal("1900.00"),
            category="Bills",
            due_date=date(2026, 8, 28),
            status="unpaid",
        )
        db_session.add(bill_soon)
        db_session.commit()

        insights = get_insights(user.id, db_session)
        insight_types = [ins["type"] for ins in insights]

        # 1. Food spending spike detected (12k to 15k = +25.00%)
        assert "spending_increase" in insight_types
        food_spike = next(ins for ins in insights if ins["type"] == "spending_increase" and ins["category"] == "Food")
        assert food_spike["pct"] == Decimal("25.00")
        assert food_spike["period"] == "this_month"

        # 2. Generic Netflix subscription price increase detected (499 -> 699 in July 2026 = +40.08%)
        assert "subscription_increase" in insight_types
        netflix_increase = next(ins for ins in insights if ins["type"] == "subscription_increase" and ins["merchant"] == "Netflix")
        assert netflix_increase["pct"] == Decimal("40.08")
        assert netflix_increase["period"] == "July 2026"

        # 3. Rent did NOT generate a false subscription increase
        landlord_increases = [ins for ins in insights if ins.get("merchant") == "Landlord"]
        assert len(landlord_increases) == 0

        # 4. Upcoming bill alert detected
        assert "upcoming_bill" in insight_types
        bill_alert = next(ins for ins in insights if ins["type"] == "upcoming_bill")
        assert bill_alert["amount"] == Decimal("1900.00")
        assert bill_alert["period"] == "within_7_days"


class TestHealthEndpoints:
    """Verifies that the health check endpoints respond with 200 and valid JSON."""

    def test_root_health_endpoint(self, client):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "finsight-backend"

    def test_api_v1_health_endpoint(self, client):
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"


class TestAdditionalEdgeCases:
    """Verifies critical edge cases across all financial engine endpoints."""

    def test_insights_empty_transactions_returns_empty_list(self, db_session: Session):
        user = User(full_name="Empty User", email="empty@example.com")
        db_session.add(user)
        db_session.commit()

        insights = get_insights(user.id, db_session)
        assert insights == []

    def test_insights_nonexistent_user_raises_value_error(self, db_session: Session):
        with pytest.raises(ValueError, match="does not exist"):
            get_insights(999999, db_session)

    def test_affordability_multiple_goals_returns_max_impact(self, db_session: Session):
        user = User(full_name="Multi Goal User", email="multigoal@example.com")
        db_session.add(user)
        db_session.flush()

        acc = Account(user_id=user.id, name="Checking", balance=Decimal("0.00"))
        db_session.add(acc)
        db_session.flush()

        tx = Transaction(
            account_id=acc.id,
            user_id=user.id,
            amount=Decimal("100000.00"),
            transaction_type="income",
            category="Other",
            transaction_date=datetime(2026, 8, 20),
        )
        db_session.add(tx)

        # Goal 1: monthly 5,000 -> 25,000 / 5,000 = 5 months
        g1 = Goal(
            user_id=user.id,
            name="Vacation",
            target_amount=Decimal("50000.00"),
            current_amount=Decimal("10000.00"),
            monthly_contribution=Decimal("5000.00"),
            status="active",
        )
        # Goal 2: monthly 10,000 -> 25,000 / 10,000 = 3 months
        g2 = Goal(
            user_id=user.id,
            name="Emergency Fund",
            target_amount=Decimal("100000.00"),
            current_amount=Decimal("20000.00"),
            monthly_contribution=Decimal("10000.00"),
            status="active",
        )
        db_session.add_all([g1, g2])
        db_session.commit()

        res = check_affordability(user.id, Decimal("25000.00"), db_session)
        assert res["can_afford"] is True
        # Max impact between 5 months (Goal 1) and 3 months (Goal 2) is 5
        assert res["savings_goal_impact_months"] == Decimal("5")

        # Verify structured goal impact facts are present in reasoning_facts
        goal_facts = [f for f in res["reasoning_facts"] if f.get("fact") == "goal_impact"]
        assert len(goal_facts) == 2
        assert any(f["goal_name"] == "Vacation" and f["impact_months"] == "5" for f in goal_facts)
        assert any(f["goal_name"] == "Emergency Fund" and f["impact_months"] == "3" for f in goal_facts)

    def test_affordability_no_active_goals_returns_zero_impact(self, db_session: Session):
        user = User(full_name="No Goal User", email="nogoal@example.com")
        db_session.add(user)
        db_session.flush()

        acc = Account(user_id=user.id, name="Checking", balance=Decimal("0.00"))
        db_session.add(acc)
        db_session.flush()

        tx = Transaction(
            account_id=acc.id,
            user_id=user.id,
            amount=Decimal("50000.00"),
            transaction_type="income",
            category="Other",
            transaction_date=datetime(2026, 8, 20),
        )
        db_session.add(tx)
        db_session.commit()

        res = check_affordability(user.id, Decimal("10000.00"), db_session)
        assert res["can_afford"] is True
        assert res["savings_goal_impact_months"] == Decimal("0")

    def test_project_goal_negative_hypothetical_contribution_raises_error(self, db_session: Session):
        user = User(full_name="Hypo User", email="hypo@example.com")
        db_session.add(user)
        db_session.flush()

        goal = Goal(
            user_id=user.id,
            name="Goal",
            target_amount=Decimal("50000.00"),
            current_amount=Decimal("10000.00"),
            monthly_contribution=Decimal("5000.00"),
            status="active",
        )
        db_session.add(goal)
        db_session.commit()

        with pytest.raises(ValueError, match="greater than zero"):
            project_goal_completion(goal.id, db_session, hypothetical_contribution=Decimal("-1000.00"))

    def test_project_goal_target_less_than_current_returns_zero(self, db_session: Session):
        user = User(full_name="Overfunded User", email="overfunded@example.com")
        db_session.add(user)
        db_session.flush()

        goal = Goal(
            user_id=user.id,
            name="Goal Overfunded",
            target_amount=Decimal("50000.00"),
            current_amount=Decimal("60000.00"),
            monthly_contribution=Decimal("5000.00"),
            status="active",
        )
        db_session.add(goal)
        db_session.commit()

        res = project_goal_completion(goal.id, db_session)
        assert res["current_months_remaining"] == Decimal("0")

    def test_spending_summary_empty_transactions_returns_zeros(self, db_session: Session):
        user = User(full_name="Empty Summary User", email="empty.summary@example.com")
        db_session.add(user)
        db_session.commit()

        res = get_spending_summary(user.id, db_session, period="this_month")
        assert res["total"] == Decimal("0.00")
        assert len(res["by_category"]) == 8
        assert all(v == Decimal("0.00") for v in res["by_category"].values())


class TestSyntheticDatasetCalculations:
    """Verifies all calculations against the actual seeded 4-month dataset."""

    @pytest.fixture
    def seeded_user_id(self, db_session: Session) -> int:
        from backend.seed.generate_synthetic_data import seed_synthetic_data
        # Seed into the main database if needed, or query demo user
        from backend.db import SessionLocal
        real_db = SessionLocal()
        try:
            demo_user = real_db.query(User).filter_by(email="aarav.sharma@example.com").first()
            if not demo_user:
                seed_synthetic_data()
                demo_user = real_db.query(User).filter_by(email="aarav.sharma@example.com").first()
            return demo_user.id
        finally:
            real_db.close()

    def test_real_database_authoritative_balance(self, seeded_user_id: int):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            bal = get_balance(seeded_user_id, db)
            assert bal["balance"] == Decimal("138372.00")
            assert bal["as_of"] == datetime(2026, 8, 26, 21, 0, 0)
        finally:
            db.close()

    def test_real_database_spending_summary(self, seeded_user_id: int):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            summary = get_spending_summary(seeded_user_id, db, period="this_month")
            assert summary["total"] == Decimal("50297.00")
            assert summary["by_category"]["Food"] == Decimal("14450.00")
            assert summary["by_category"]["Bills"] == Decimal("27969.00")
            assert summary["by_category"]["Shopping"] == Decimal("4289.00")
            assert summary["by_category"]["Transport"] == Decimal("1770.00")
            assert summary["by_category"]["Entertainment"] == Decimal("699.00")
            assert summary["by_category"]["Healthcare"] == Decimal("1120.00")
            assert summary["vs_last_period_pct"]["Food"] == Decimal("21.94")

            # Last month
            last_summary = get_spending_summary(seeded_user_id, db, period="last_month")
            assert last_summary["total"] == Decimal("48567.00")
            assert last_summary["by_category"]["Food"] == Decimal("11850.00")
        finally:
            db.close()

    def test_real_database_affordability(self, seeded_user_id: int):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            # 5,000 INR purchase is affordable
            aff_5k = check_affordability(seeded_user_id, Decimal("5000.00"), db)
            assert aff_5k["can_afford"] is True
            assert aff_5k["balance_after"] == Decimal("133372.00")
            assert aff_5k["upcoming_bills"] == Decimal("6529.00")
            assert aff_5k["savings_goal_impact_months"] == Decimal("1")

            # 200,000 INR purchase is unaffordable
            aff_200k = check_affordability(seeded_user_id, Decimal("200000.00"), db)
            assert aff_200k["can_afford"] is False
            assert aff_200k["balance_after"] == Decimal("-61628.00")
        finally:
            db.close()

    def test_real_database_goal_projection(self, seeded_user_id: int):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            user = db.query(User).filter_by(id=seeded_user_id).first()
            emergency_goal = next(g for g in user.goals if g.name == "Emergency Fund")

            proj = project_goal_completion(emergency_goal.id, db)
            assert proj["current_months_remaining"] == Decimal("11")

            proj_hypo = project_goal_completion(emergency_goal.id, db, hypothetical_contribution=Decimal("15000.00"))
            assert proj_hypo["hypothetical_months_remaining"] == Decimal("7")
        finally:
            db.close()

    def test_real_database_insights(self, seeded_user_id: int):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            insights = get_insights(seeded_user_id, db)

            # Food spending spike (+21.94%)
            food_spikes = [ins for ins in insights if ins["type"] == "spending_increase" and ins.get("category") == "Food"]
            assert len(food_spikes) == 1
            assert food_spikes[0]["pct"] == Decimal("21.94")

            # Netflix subscription hike (+40.08% in July 2026)
            netflix_hikes = [ins for ins in insights if ins["type"] == "subscription_increase" and ins.get("merchant") == "Netflix"]
            assert len(netflix_hikes) == 1
            assert netflix_hikes[0]["pct"] == Decimal("40.08")
            assert netflix_hikes[0]["period"] == "July 2026"
        finally:
            db.close()

