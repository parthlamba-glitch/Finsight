"""
Unit tests for AI Explainer Grounding Validation.

Verifies:
1. Legitimate datetime values in authoritative facts allow valid date narration.
2. Legitimate date values in authoritative facts allow valid date narration.
3. Existing numeric financial facts pass validation.
4. Genuinely hallucinated numbers/percentages are strictly rejected.
"""

from datetime import date, datetime
from decimal import Decimal
import pytest

from ai.explainer import (
    validate_explanation_grounding,
    _extract_numbers_from_obj,
    _extract_numbers_from_text,
)


class TestExplainerGroundingValidation:
    """Test suite for grounding validation in ai/explainer.py."""

    def test_extract_numbers_from_datetime(self):
        """Authoritative fact containing a datetime object should expose its date/time numbers."""
        fact = {
            "intent": "get_balance",
            "balance": Decimal("138372.00"),
            "as_of": datetime(2026, 8, 26, 21, 0),
        }
        allowed = _extract_numbers_from_obj(fact)

        assert 138372.0 in allowed
        assert 2026.0 in allowed
        assert 8.0 in allowed
        assert 26.0 in allowed

    def test_extract_numbers_from_date(self):
        """Authoritative fact containing a date object should expose its year/month/day numbers."""
        fact = {
            "intent": "check_affordability",
            "due_date": date(2026, 9, 15),
            "amount": Decimal("2500.00"),
        }
        allowed = _extract_numbers_from_obj(fact)

        assert 2500.0 in allowed
        assert 2026.0 in allowed
        assert 9.0 in allowed
        assert 15.0 in allowed

    def test_valid_balance_with_iso_datetime_accepted(self):
        """A response stating the balance and ISO date should be accepted."""
        fact = {
            "intent": "get_balance",
            "balance": Decimal("138372.00"),
            "as_of": datetime(2026, 8, 26, 21, 0),
        }
        answer = "Your current balance is ₹138,372.00 as of 2026-08-26."
        is_valid = validate_explanation_grounding(answer, fact, "What's my balance?")
        assert is_valid is True

    def test_valid_balance_with_natural_date_accepted(self):
        """A response stating the balance and natural date should be accepted."""
        fact = {
            "intent": "get_balance",
            "balance": Decimal("138372.00"),
            "as_of": datetime(2026, 8, 26, 21, 0),
        }
        answer = "Your balance is ₹138,372 as of August 26, 2026."
        is_valid = validate_explanation_grounding(answer, fact, "What's my balance?")
        assert is_valid is True

    def test_existing_numeric_financial_facts_accepted(self):
        """Authoritative calculations with multiple financial numbers should be accepted."""
        fact = {
            "intent": "check_affordability",
            "amount": Decimal("8000.00"),
            "can_afford": True,
            "balance_after": Decimal("130372.00"),
            "upcoming_bills_total": Decimal("6529.00"),
            "impact_on_goals": [
                {"goal_name": "Emergency Fund", "delay_months": 1}
            ],
        }
        answer = (
            "Yes, you can afford this purchase of ₹8,000.00. Your remaining balance "
            "will be ₹130,372.00 with ₹6,529.00 reserved for upcoming bills. "
            "This may delay your Emergency Fund by 1 month."
        )
        is_valid = validate_explanation_grounding(
            answer, fact, "Could I comfortably buy an ₹8,000 pair of headphones right now?"
        )
        assert is_valid is True

    def test_hallucinated_balance_rejected(self):
        """A response inventing a non-existent balance number must be rejected."""
        fact = {
            "intent": "get_balance",
            "balance": Decimal("138372.00"),
            "as_of": datetime(2026, 8, 26, 21, 0),
        }
        answer = "Your current balance is ₹250,000.00 as of August 26, 2026."
        is_valid = validate_explanation_grounding(answer, fact, "What's my balance?")
        assert is_valid is False

    def test_hallucinated_interest_or_percentage_rejected(self):
        """A response adding unsupported percentages must be rejected."""
        fact = {
            "intent": "get_spending_summary",
            "total": Decimal("50297.00"),
            "period": "this_month",
        }
        answer = "You spent ₹50,297.00 this month, which is 15% higher than usual."
        is_valid = validate_explanation_grounding(answer, fact, "How much did I spend?")
        assert is_valid is False

    def test_temporal_period_contradiction_rejected(self):
        """A response claiming 'this month' when facts are 'last_month' must be rejected."""
        fact = {
            "intent": "get_spending_summary",
            "total": Decimal("42000.00"),
            "period": "last_month",
        }
        answer = "You spent ₹42,000.00 this month."
        is_valid = validate_explanation_grounding(answer, fact, "How much did I spend last month?")
        assert is_valid is False
