"""
Deterministic Insight Detection and Structured Fact Helpers for FinSight.

NOTE: This module contains ONLY deterministic heuristics and structured data helpers.
It does NOT contain spoken-text formatting or LLM narration logic.

Data flow:
Database -> Deterministic Engine -> Structured Financial Facts (this module) -> LLM Narration -> TTS
"""

from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import date


def build_insight_fact(
    insight_type: str,
    severity: str,
    category: Optional[str],
    metric_name: str,
    metric_value: Decimal,
    threshold_value: Optional[Decimal] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Constructs a standardized structured insight fact dictionary.

    Args:
        insight_type: Category of insight (e.g., 'spending_spike', 'bill_due_soon', 'goal_milestone').
        severity: Level of importance ('INFO', 'WARNING', 'CRITICAL').
        category: Relevant spending category or None.
        metric_name: Description of the evaluated metric.
        metric_value: Numeric value (Decimal) of the metric.
        threshold_value: Optional reference benchmark or limit.
        metadata: Additional contextual facts (dates, vendor names, etc.).

    Returns:
        Structured dictionary representing pure financial facts.
    """
    return {
        "insight_type": insight_type,
        "severity": severity,
        "category": category,
        "metric_name": metric_name,
        "metric_value": str(metric_value),
        "threshold_value": str(threshold_value) if threshold_value is not None else None,
        "metadata": metadata or {},
    }
