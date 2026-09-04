"""
Unit tests for fast-path query normalization and robust balance intent detection.

Verifies:
1. Normalization of whitespace, curly apostrophes ('’', '‘'), trailing punctuation, and 'whats' -> "what's".
2. Direct balance inquiries route immediately via _fast_path_match to 'get_balance' without calling Gemini.
3. Spending, purchase, affordability, transfer, and cost queries NEVER route to 'get_balance'.
"""

import pytest
from ai.intent_router import _fast_path_match, route_query


POSITIVE_BALANCE_QUERIES = [
    "What's my balance?",
    "whats my balance",
    "what’s my balance",
    "What is my balance?",
    "check my balance",
    "check my account balance",
    "tell me my balance please",
    "how much money do I have",
    "how much do I have",
    "how much is in my account",
]

NEGATIVE_BALANCE_QUERIES = [
    "Can I afford headphones for ₹8,000?",
    "Can I afford to spend ₹5,000?",
    "How much did I spend?",
    "How much did I spend this month?",
    "How much did I spend on food?",
    "How much does this cost?",
    "Can I buy this?",
    "Can I send ₹500 to Alex?",
    "Transfer ₹1,000",
    "Pay ₹500 to Alex",
]


class TestFastPathBalanceMatching:
    """Verifies that unambiguous balance inquiries match the fast path and non-balance queries do not."""

    @pytest.mark.parametrize("query", POSITIVE_BALANCE_QUERIES)
    def test_positive_balance_queries_match_fast_path(self, query: str):
        result = _fast_path_match(query)
        assert result is not None, f"Query failed to match fast path: {query}"
        assert result.get("status") == "success", f"Unexpected status for query '{query}': {result}"
        assert result.get("function_name") == "get_balance", (
            f"Query '{query}' routed to '{result.get('function_name')}' instead of 'get_balance'"
        )
        assert result.get("arguments") == {}

    @pytest.mark.parametrize("query", NEGATIVE_BALANCE_QUERIES)
    def test_negative_balance_queries_never_route_to_get_balance(self, query: str):
        result = _fast_path_match(query)
        if result is not None:
            # If it matches another fast path (e.g. check_affordability, get_spending_summary),
            # it MUST NOT be get_balance.
            assert result.get("function_name") != "get_balance", (
                f"Negative query '{query}' incorrectly matched 'get_balance' in fast path!"
            )

    @pytest.mark.parametrize("query", POSITIVE_BALANCE_QUERIES)
    def test_route_query_returns_fast_path_mode(self, query: str):
        """Ensures route_query resolves in FAST_PATH mode with 0ms LLM overhead."""
        res = route_query(query=query, user_id="1")
        assert res.get("status") == "success"
        assert res.get("function_name") == "get_balance"
        assert res.get("router_mode") == "FAST_PATH"
        assert "timing_ms" in res
