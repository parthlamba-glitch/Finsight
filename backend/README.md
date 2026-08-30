# FinSight Backend Foundation

Accessibility-First, Voice-First Financial Copilot Backend built with Python, FastAPI, SQLAlchemy, and SQLite.

---

## 1. Project Structure

```
backend/
├── main.py                          # FastAPI application entrypoint & lifespan configuration
├── db.py                            # SQLite database engine, SessionLocal, Base, and get_db dependency
├── models/                          # SQLAlchemy ORM models
│   ├── __init__.py                  # Model exports and validation sets
│   ├── user.py                      # User model with mandatory accessibility_prefs JSON
│   ├── account.py                   # Account model with cached balance & monthly_income
│   ├── transaction.py               # Transaction model with signed amounts & category constraints
│   ├── goal.py                      # Goal model with Decimal amounts & statuses
│   ├── bill.py                      # Bill model with due date indexes & status semantics
│   └── document.py                  # Document model for metadata & extracted facts storage
├── engine/                          # Deterministic Financial Engine (pure Python, zero LLM)
│   ├── __init__.py                  # Public engine function exports
│   ├── financial_engine.py          # Public API function signatures (stubs for Day 2)
│   ├── insights.py                  # Structured insight detection & fact builders
│   └── tests/                       # Foundation test suite
│       ├── conftest.py              # Test fixtures (StaticPool in-memory SQLite)
│       └── test_engine.py           # Foundation tests for schema, relationships, & signatures
├── seed/
│   └── generate_synthetic_data.py   # Synthetic data generator with deterministic opening balance
├── routers/                         # FastAPI route handlers
│   ├── dashboard.py                 # Dashboard endpoints scaffold
│   └── goals.py                     # Goals endpoints scaffold
├── requirements.txt                 # Backend Python dependencies
└── README.md                        # Documentation & setup guide
```

---

## 2. Core Financial Data Conventions

### 2.1 Non-Negotiable Money Sign Convention
All monetary values in the database are stored using `Numeric(12, 2)` (never float).

- **Positive amount (`+`)**: Money **entering** the account (inflows).
  - Salary Credit: `+75000.00`
  - Opening Balance: `+25000.00`
  - Merchant Refund: `+450.00`
- **Negative amount (`-`)**: Money **leaving** the account (outflows).
  - Rent Payment: `-25000.00`
  - Groceries: `-4200.00`
  - Food Delivery: `-620.00`
  - Electricity Bill: `-1850.00`

### 2.2 Authoritative Balance Definition
- **Authoritative Balance** = `SUM(transaction.amount)` across all transactions belonging to the user's accounts.
- `accounts.balance` is strictly a **cached/display field** for UI presentation and is **never** used by the deterministic financial engine for math or decision making.
- To ensure 100% deterministic calculations from day zero, accounts are initialized with an explicit **Opening Balance** transaction (`+25000.00`).

### 2.3 Transaction Categories & Types
- **Types**: `income`, `expense`
- **Categories**: `Food`, `Transport`, `Shopping`, `Bills`, `Entertainment`, `Healthcare`, `Education`, `Other`

---

## 3. Deterministic Engine Public API Contract

All financial computations are performed deterministically in Python. The public API consists of plain functions:

```python
def get_balance(user_id: int, db: Session) -> dict: ...
def get_spending_summary(user_id: int, db: Session, period: str = "this_month") -> dict: ...
def check_affordability(user_id: int, amount: Decimal, db: Session) -> dict: ...
def project_goal_completion(goal_id: int, db: Session, hypothetical_contribution: Optional[Decimal] = None) -> dict: ...
def get_insights(user_id: int, db: Session) -> list: ...
```

---

## 4. Quickstart Guide

### Prerequisites
- Python 3.10+ (tested on Python 3.11)

### Installation
From the repository root (`finsight`):

```bash
pip install -r backend/requirements.txt
```

### Run Tests
Execute the foundation tests:

```bash
pytest backend/engine/tests/ -v
```

### Seed Synthetic Financial Data
Populate the SQLite database (`finsight.db`) with rich demo data:

```bash
python -m backend.seed.generate_synthetic_data
```

### Run the FastAPI Server
Start the local development server:

```bash
uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
```

Or execute directly:

```bash
python backend/main.py
```

### Health Check Endpoints
- Root Health: `GET http://127.0.0.1:8000/health`
- API v1 Health: `GET http://127.0.0.1:8000/api/v1/health`
- Interactive API Docs: `http://127.0.0.1:8000/docs`
