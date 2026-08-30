"""
Pydantic Schemas for FinSight API layer.

Defines typed request and response schemas with Decimal-safe precision and JSON serialization.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field


class GoalCreateRequest(BaseModel):
    """Request payload for creating a new financial goal."""
    user_id: int = Field(..., description="ID of the user who owns the goal")
    name: str = Field(..., min_length=1, max_length=255, description="Name of the financial goal")
    target_amount: Decimal = Field(..., gt=0, description="Target savings amount (must be positive)")
    monthly_contribution: Decimal = Field(..., gt=0, description="Monthly planned contribution (must be positive)")
    target_date: Optional[date] = Field(None, description="Optional target completion date")


class GoalUpdateRequest(BaseModel):
    """Request payload for updating a financial goal's contribution."""
    monthly_contribution: Decimal = Field(..., gt=0, description="Updated monthly contribution amount (must be positive)")
    user_id: Optional[int] = Field(None, description="Optional user_id for explicit ownership verification")


class GoalResponse(BaseModel):
    """Response model for a single financial goal."""
    id: int
    user_id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    monthly_contribution: Decimal
    currency: str = "INR"
    target_date: Optional[date] = None
    status: str
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GoalProjection(BaseModel):
    """Goal projection completion facts computed by the deterministic engine."""
    current_months_remaining: Decimal
    hypothetical_months_remaining: Optional[Decimal] = None


class GoalWithProjectionResponse(BaseModel):
    """Response model returning an updated goal along with its deterministic projection."""
    goal: GoalResponse
    projection: GoalProjection


class TransactionResponse(BaseModel):
    """Response model for a single financial transaction."""
    id: int
    account_id: int
    user_id: int
    amount: Decimal
    currency: str = "INR"
    transaction_type: str
    category: str
    merchant_name: Optional[str] = None
    description: Optional[str] = None
    source: str = "bank"
    reference_id: Optional[str] = None
    transaction_date: datetime
    is_suspicious: bool = False

    model_config = ConfigDict(from_attributes=True)


class TransactionsListResponse(BaseModel):
    """Response model for transaction history and categorical spending breakdown."""
    transactions: List[TransactionResponse]
    by_category: Dict[str, Decimal]


class DashboardOverviewResponse(BaseModel):
    """
    Response model for user dashboard overview.

    Definition of terms:
    - balance: Authoritative balance derived from SUM(transaction.amount).
    - monthly_income: Sum of monthly_income across active accounts.
    - monthly_spending: Sourced from get_spending_summary(user_id, period='this_month')['total'].
    - monthly_surplus: Authoritative calculated cash-flow metric defined strictly as
      (monthly_income - monthly_spending) for the period.
    - savings: Legacy compatibility field equivalent to monthly_surplus (cash-flow surplus
      for the period, NOT confirmed deposits into a savings account).
    - upcoming_bills: Unpaid bills due within 30 days of the deterministic as_of date.
    - goals: List of active financial goals.
    """
    balance: Decimal = Field(..., description="Authoritative balance from transaction history")
    monthly_income: Decimal = Field(..., description="Total monthly income from active accounts")
    monthly_spending: Decimal = Field(..., description="Total expenses for the current month")
    monthly_surplus: Decimal = Field(..., description="Authoritative monthly cash-flow surplus (monthly_income - monthly_spending)")
    savings: Decimal = Field(..., description="Compatibility alias for monthly_surplus (cash-flow surplus, not savings-account deposits)")
    upcoming_bills: Decimal = Field(..., description="Total unpaid bills due within 30 days")
    goals: List[GoalResponse] = Field(..., description="List of active savings and financial goals")


# --- Day 4B Ingestion Schemas ---

class VoiceTransactionRequest(BaseModel):
    """Request payload from voice/AI layer to ingest a structured transaction."""
    user_id: int = Field(..., description="ID of the user")
    account_id: Optional[int] = Field(None, description="Optional account ID (auto-assigns to active account if None)")
    amount: Decimal = Field(..., gt=0, description="Positive transaction amount")
    transaction_type: str = Field(..., description="'expense' or 'income'")
    category: str = Field("Other", description="Transaction category (Food, Transport, Shopping, Bills, etc.)")
    merchant_name: Optional[str] = Field(None, description="Payee / Merchant name")
    description: Optional[str] = Field(None, description="Transaction description or voice note")
    transaction_date: Optional[datetime] = Field(None, description="Transaction date/time (defaults to now)")


class BankConnectRequest(BaseModel):
    """Request payload to connect a user's account to a mock financial institution."""
    user_id: int = Field(..., description="ID of the user")
    institution_name: str = Field("HDFC Bank Mock", description="Mock bank institution name")
    account_id: Optional[int] = Field(None, description="Optional account ID to link")


class BankConnectResponse(BaseModel):
    """Response model for mock bank connection."""
    status: str
    institution_name: str
    user_id: int
    account_id: int
    message: str


class SkippedTransactionItem(BaseModel):
    """Details of a skipped duplicate transaction."""
    reference_id: Optional[str] = None
    merchant_name: Optional[str] = None
    amount: str
    reason: Optional[str] = None
    existing_transaction_id: Optional[int] = None


class BankSyncRequest(BaseModel):
    """Request payload to trigger mock bank feed synchronization."""
    user_id: int = Field(..., description="ID of the user")
    account_id: Optional[int] = Field(None, description="Optional account ID to sync")


class BankSyncResponse(BaseModel):
    """Response model for bank feed synchronization."""
    status: str
    user_id: int
    account_id: int
    imported_count: int
    duplicate_count: int
    skipped_count: int
    imported_transactions: List[TransactionResponse]
    skipped_transactions: List[SkippedTransactionItem]


class StatementCandidateItem(BaseModel):
    """Single extracted statement transaction candidate."""
    reference_id: Optional[str] = Field(None, description="Unique reference ID extracted from statement")
    amount: Decimal = Field(..., gt=0, description="Positive transaction amount")
    transaction_type: str = Field("expense", description="'expense' or 'income'")
    category: str = Field("Other", description="Transaction category")
    merchant_name: Optional[str] = Field(None, description="Payee / Merchant name")
    description: Optional[str] = Field(None, description="Transaction description")
    transaction_date: datetime = Field(..., description="Extracted transaction timestamp")


class StatementEvaluatedCandidate(BaseModel):
    """Candidate transaction with duplicate evaluation status."""
    candidate_id: str
    reference_id: Optional[str] = None
    amount: Decimal
    transaction_type: str
    category: str
    merchant_name: Optional[str] = None
    description: Optional[str] = None
    transaction_date: datetime
    is_duplicate: bool = False
    duplicate_reason: Optional[str] = None


class StatementUploadRequest(BaseModel):
    """Request payload uploading extracted candidates from a statement."""
    user_id: int = Field(..., description="ID of the user")
    account_id: Optional[int] = Field(None, description="Target account ID")
    filename: str = Field(..., description="Original statement filename")
    extracted_candidates: List[StatementCandidateItem] = Field(default_factory=list, description="Extracted transaction candidate list")


class StatementUploadResponse(BaseModel):
    """Response model staging statement candidates for user confirmation."""
    document_id: int
    filename: str
    total_candidates: int
    valid_candidates_count: int
    duplicate_candidates_count: int
    candidates: List[StatementEvaluatedCandidate]


class ConfirmTransactionsRequest(BaseModel):
    """Request payload to confirm and persist validated statement candidates."""
    user_id: int = Field(..., description="ID of the user")
    account_id: Optional[int] = Field(None, description="Target account ID")
    document_id: Optional[int] = Field(None, description="Optional associated document ID")
    candidates: List[StatementCandidateItem] = Field(..., min_length=1, description="List of candidates to confirm and persist")


class ConfirmTransactionsResponse(BaseModel):
    """Response model confirming persisted transactions."""
    status: str
    confirmed_count: int
    skipped_duplicates_count: int
    transactions: List[TransactionResponse]
    skipped_items: List[SkippedTransactionItem]


# --- Day 5 AI & Payment Schemas ---

class AskRequest(BaseModel):
    """Request payload for natural language and voice queries to /ask."""
    query: str = Field(..., min_length=1, description="Natural language question, command, or confirmation")
    user_id: Optional[int] = Field(None, description="Legacy demo user ID (strictly ignored when JWT Bearer token is provided)")
    voice: bool = Field(False, description="Whether the request was spoken via voice UI")
    confirmation_token: Optional[str] = Field(None, description="Optional pending payment confirmation ID or token")
    conversation_id: Optional[str] = Field(None, description="Optional multi-turn conversation session ID")


class AskResponse(BaseModel):
    """Response model returning accessible natural narration backed by deterministic facts."""
    intent: str = Field(..., description="Classified intent")
    answer_text: str = Field(..., description="Accessible spoken answer for screen reader / TTS")
    aria_priority: str = Field("polite", description="'polite' or 'assertive' for live regions")
    requires_confirmation: bool = Field(False, description="Whether explicit user confirmation is needed")
    confirmation_token: Optional[str] = Field(None, description="Token/ID required for confirmation step")
    pending_payment_id: Optional[int] = Field(None, description="Database ID of the pending payment")
    structured_facts: Dict[str, Any] = Field(default_factory=dict, description="Authoritative structured engine facts")
    structured_data: Dict[str, Any] = Field(default_factory=dict, description="Authoritative structured engine facts (alias for structured_facts)")
    execution_mode: str = Field("MOCK_FALLBACK", description="Execution mode: 'REAL_LLM' or 'MOCK_FALLBACK'")
    conversation_status: str = Field("completed", description="Conversation status: 'completed', 'clarification_needed', or 'awaiting_confirmation'")
    conversation_id: Optional[str] = Field(None, description="Conversation session ID")


class PaymentPreviewRequest(BaseModel):
    """Request payload to preview a payment without creating transactions."""
    amount: Decimal = Field(..., gt=0, description="Payment amount (positive Decimal)")
    recipient_name: str = Field(..., min_length=1, max_length=255, description="Target recipient or payee name")
    user_id: Optional[int] = Field(None, description="Legacy demo user ID (strictly overridden by authenticated JWT)")


class PaymentPreviewResponse(BaseModel):
    """Response model returning deterministic preview, risk evaluation, and pending payment ID."""
    can_proceed: bool
    amount: Decimal
    recipient_name: str
    current_balance: Decimal
    balance_after: Decimal
    upcoming_bills: Decimal
    available_after_commitments: Decimal
    risk_level: str
    fraud_warning: bool = False
    risk_reasons: List[str] = Field(default_factory=list)
    pending_payment_id: Optional[int] = None
    requires_confirmation: bool = True
    confirmation_token: Optional[str] = None
    reasoning_facts: List[Dict[str, Any]] = Field(default_factory=list)


class PaymentExecuteRequest(BaseModel):
    """Request payload to execute a persistent pending payment."""
    pending_payment_id: int = Field(..., description="Persistent ID of the pending payment to execute")
    user_id: Optional[int] = Field(None, description="Legacy demo user ID (strictly verified against authenticated JWT)")


class PaymentExecuteResponse(BaseModel):
    """Response model for completed simulated payment transaction."""
    success: bool = True
    transaction_id: int
    recipient_name: str
    amount: Decimal
    previous_balance: Decimal
    new_balance: Decimal
    transaction_type: str = "expense"
    pending_payment_id: int
    status: str = "executed"


# --- Authentication & Passkey Schemas ---

class UserSignupRequest(BaseModel):
    """Request payload for new user registration."""
    name: str = Field(..., min_length=1, max_length=255, description="User full name")
    email: str = Field(..., min_length=3, max_length=255, description="User unique email address")
    password: str = Field(..., min_length=8, max_length=255, description="Secure user password (minimum 8 chars)")
    accessibility_prefs: Optional[Dict[str, Any]] = Field(None, description="Optional accessibility preferences")


class UserLoginRequest(BaseModel):
    """Request payload for password-based login."""
    email: str = Field(..., description="Registered user email")
    password: str = Field(..., description="User plaintext password to verify")


class UserResponse(BaseModel):
    """Safe response model for user profile (never exposes passwords or credentials)."""
    id: int
    full_name: str
    email: str
    accessibility_prefs: Dict[str, Any]
    is_active: bool = True
    has_passkey: bool = False
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """Response model returning JWT access token upon successful authentication."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PasskeyRegisterVerifyRequest(BaseModel):
    """Request payload verifying a WebAuthn registration credential from browser."""
    credential: Dict[str, Any] = Field(..., description="WebAuthn credential object from navigator.credentials.create")
    challenge: str = Field(..., description="Challenge string received in registration options")
    nickname: Optional[str] = Field("My Passkey", description="User-friendly name for this authenticator/device")


class PasskeyLoginOptionsRequest(BaseModel):
    """Request payload requesting authentication options for passkey sign-in."""
    email: Optional[str] = Field(None, description="Optional email address to filter allowed credentials")


class PasskeyLoginVerifyRequest(BaseModel):
    """Request payload verifying WebAuthn authentication assertion from browser."""
    credential: Dict[str, Any] = Field(..., description="WebAuthn assertion object from navigator.credentials.get")
    challenge: str = Field(..., description="Challenge string received in login options")


class PasskeyCredentialResponse(BaseModel):
    """Response model describing a registered passkey credential."""
    id: int
    nickname: Optional[str] = None
    created_at: datetime
    last_used_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)




