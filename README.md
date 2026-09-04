

```markdown
# 💰 FinSight

### An AI-Powered, Accessibility-First, Voice-First Personal Finance Assistant

> **Understand your money. Ask naturally. Make better financial decisions.**

FinSight is an AI-powered personal finance assistant designed to make financial management simpler, more accessible, and more conversational.

Instead of navigating through complicated financial dashboards, users can simply **ask questions in natural language or by voice**.

For example:

> 🎙️ *"Can I afford headphones for ₹8,000?"*

> 🎙️ *"How much did I spend on food this month?"*

> 🎙️ *"When will I reach my emergency fund goal?"*

> 🎙️ *"Send ₹5,000 to Dr Rao."*

FinSight combines **AI-powered natural-language understanding** with a **deterministic financial engine**, ensuring that conversational AI never compromises the accuracy of financial calculations.

---

## ✨ Features

### 🎙️ Voice-First Interaction

Interact with your finances naturally using speech.

```text
🎤 User speaks
      ↓
🗣️ Speech-to-Text
      ↓
🤖 AI Intent Understanding
      ↓
⚙️ Financial Engine
      ↓
💬 Grounded Response
      ↓
🔊 Text-to-Speech
```

FinSight is designed around accessibility and conversational interaction, allowing users to interact with their finances without relying entirely on traditional dashboards.

---

### 🤖 Natural Language Financial Assistant

Users don't need to remember specific commands.

FinSight understands requests such as:

- "What's my balance?"
- "How much did I spend this month?"
- "Can I afford ₹8,000?"
- "When will I reach my emergency fund?"
- "Give me insights about my spending."
- "Send ₹5,000 to Dr Rao."

The AI layer converts natural language into structured intents and parameters that the backend can safely process.

---

### 🧮 Deterministic Financial Engine

Financial calculations are **not performed by the LLM**.

The backend financial engine is the single source of truth for:

- Account balance
- Spending summaries
- Affordability checks
- Goal projections
- Financial insights

```text
User Query
    ↓
AI understands WHAT the user wants
    ↓
Backend determines the actual financial facts
    ↓
AI explains those facts naturally
```

This separation keeps financial calculations deterministic, reproducible, and grounded in actual database data.

---

### 💳 Safe Payment Flow

Payments follow a preview → confirmation → execution workflow.

```text
User requests payment
        ↓
Payment Preview
        ↓
User sees/hears details
        ↓
Explicit Confirmation
        ↓
Payment Execution
        ↓
Transaction recorded
```

A natural-language request alone does **not** execute a payment.

The payment system is implemented as a simulated payment engine and records successful payments in the transaction ledger.

---

### 🏦 Transaction Ingestion

FinSight supports transactions from multiple sources:

- 🏦 Bank synchronization
- 📄 Bank statement uploads
- 🎙️ Voice transactions
- 💳 Payments
- ✍️ Manual transactions

All transactions ultimately enter the same authoritative transaction ledger.

Each transaction records its source and can contain a reference ID for deterministic deduplication.

---

### 🔁 Transaction Normalization & Deduplication

Incoming transactions are normalized before being persisted.

The ingestion pipeline handles:

- Amount validation
- Transaction sign normalization
- Merchant normalization
- Category validation
- Date validation
- Source attribution
- Reference IDs

Repeated bank synchronization does not create duplicate transactions.

Deduplication uses deterministic matching across transaction sources.

---

### 📄 Bank Statement Processing

Statement uploads use a staged transaction workflow:

```text
Statement Upload
      ↓
Transaction Extraction
      ↓
Candidate Transactions
      ↓
User Confirmation
      ↓
Transactions Persisted
```

Extracted transactions are staged first and only become part of the authoritative transaction ledger after confirmation.

This prevents incorrect document extraction from silently modifying financial data.

---

### 🎯 Financial Goals

FinSight supports financial goal management.

Users can:

- Create financial goals
- Track progress
- Set target amounts
- Set target dates
- Define monthly contributions
- Project goal completion

For example:

> *"When will I reach my emergency fund goal if I contribute ₹10,000 every month?"*

The projection is calculated by the deterministic backend engine.

---

### 📊 Financial Insights

FinSight provides financial insights based on actual transaction data.

The backend can analyze:

- Current balance
- Income
- Spending
- Savings/surplus
- Spending categories
- Financial goals
- Upcoming bills

The AI layer then turns these structured facts into natural, user-friendly explanations.

---

### 🚨 Scam Analysis

FinSight can analyze suspicious financial content using AI and pattern-based reasoning.

The system can help users identify potentially suspicious messages and financial requests and provide an understandable explanation of the warning signs.

The scam checker is designed as an analysis and warning system rather than a guaranteed fraud detector.

---

## 🏗️ Architecture

FinSight follows a layered architecture where each component has a clearly defined responsibility.

```text
                         ┌─────────────────────┐
                         │      Frontend       │
                         │                     │
                         │ UI / Voice / TTS    │
                         └──────────┬──────────┘
                                    │
                                    │ User Query
                                    ▼
                         ┌─────────────────────┐
                         │     AI Layer        │
                         │                     │
                         │ Intent Understanding│
                         │ Parameter Extraction│
                         │ Response Generation │
                         └──────────┬──────────┘
                                    │
                                    │ Structured Intent
                                    ▼
                         ┌─────────────────────┐
                         │ Backend Dispatcher  │
                         │                     │
                         │ Intent → Action     │
                         └──────────┬──────────┘
                                    │
                  ┌─────────────────┼─────────────────┐
                  │                 │                 │
                  ▼                 ▼                 ▼
          ┌─────────────┐   ┌─────────────┐   ┌─────────────┐
          │ Financial   │   │   Payment   │   │  Ingestion  │
          │   Engine    │   │   Engine    │   │   Pipeline  │
          └──────┬──────┘   └──────┬──────┘   └──────┬──────┘
                 │                 │                 │
                 └─────────────────┼─────────────────┘
                                   ▼
                         ┌─────────────────────┐
                         │      Database       │
                         │                     │
                         │ SQLite + SQLAlchemy │
                         └─────────────────────┘
```

---

## 🧠 AI ↔ Backend Responsibility

A major design principle of FinSight is the separation between **language intelligence** and **financial authority**.

### AI Layer

The AI is responsible for:

- Understanding natural language
- Identifying user intent
- Extracting parameters
- Understanding goal names
- Generating natural-language explanations
- Asking clarification questions
- Analyzing suspicious content
- Producing speech-friendly responses

### Backend

The backend is responsible for:

- Database access
- User/account isolation
- Financial calculations
- Transaction persistence
- Deduplication
- Goal resolution
- Payment preview
- Payment execution
- Data validation

### 🚫 AI Does Not

The AI does not act as the financial source of truth.

It does not:

- Invent account balances
- Invent transactions
- Directly query the database
- Perform authoritative financial calculations
- Directly execute payments

The backend remains responsible for authoritative financial operations.

---

## 🗄️ Database

FinSight uses:

**SQLite + SQLAlchemy**

The main database is:

```text
finsight.db
```

### Core Tables

```text
users
accounts
transactions
goals
bills
documents
```

### Transaction Ledger

Transactions use signed amounts:

```text
Income       → +₹75,000
Expense      → -₹25,000
Refund       → +₹850
```

The authoritative balance is calculated from the transaction ledger:

```text
Balance = SUM(all transaction amounts)
```

This keeps the financial state consistent across transactions, bank synchronization, statements, and payments.

---

## 📁 Project Structure

```text
FinSight/
│
├── ai/
│   ├── intent_router.py
│   ├── fake_engine.py
│   ├── explainer.py
│   ├── pipeline.py
│   └── live_demo.py
│
├── backend/
│   ├── db.py
│   ├── models.py
│   ├── schemas.py
│   ├── main.py
│   │
│   ├── engine/
│   │   ├── financial_engine.py
│   │   ├── insights.py
│   │   └── dispatcher.py
│   │
│   ├── ingestion/
│   │   ├── normalizer.py
│   │   ├── deduplicator.py
│   │   └── bank_sync.py
│   │
│   ├── payment/
│   │   └── payment_engine.py
│   │
│   ├── routers/
│   │   ├── dashboard.py
│   │   ├── transactions.py
│   │   ├── goals.py
│   │   ├── bank.py
│   │   ├── statements.py
│   │   └── ai.py
│   │
│   └── tests/
│
├── finsight.db
├── requirements.txt
└── README.md
```

---

## 🔌 API

The backend is built using **FastAPI**.

The API provides endpoints for:

- Dashboard and financial overview
- Transactions
- Goals
- Bank synchronization
- Statement uploads
- Voice transactions
- Payment workflows
- AI-powered financial queries

FastAPI's interactive documentation is available at:

```text
http://127.0.0.1:8000/docs
```

---

## 🧮 Financial Engine

The deterministic financial engine provides:

```python
get_balance(user_id, db)

get_spending_summary(
    user_id,
    db,
    period="this_month"
)

check_affordability(
    user_id,
    amount,
    db
)

project_goal_completion(
    goal_id,
    db,
    hypothetical_contribution=None
)

get_insights(
    user_id,
    db
)
```

All monetary calculations use `Decimal` internally to avoid floating-point precision issues.

---

## 🧪 Testing

FinSight includes automated backend tests covering:

- Database initialization
- Financial calculations
- Balance calculation
- Spending summaries
- Affordability checks
- Goal projections
- Financial insights
- Payment preview
- Payment execution
- Payment safety
- Transaction ingestion
- Bank synchronization
- Statement processing
- Transaction confirmation
- Deduplication
- User isolation
- Regression cases

Run the tests with:

```bash
.venv\Scripts\python -m pytest -v
```

---

## 🚀 Getting Started

### Prerequisites

Make sure you have:

- Python 3.10+
- Git
- pip

### 1. Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd FinSight
```

### 2. Create a Virtual Environment

Windows:

```bash
python -m venv .venv
.venv\Scripts\activate
```

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Start the FastAPI Server

```bash
uvicorn backend.main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Interactive documentation:

```text
http://127.0.0.1:8000/docs
```

---

## 🎬 Example Interaction

### User

> "Can I afford headphones for ₹8,000?"

### AI

```json
{
  "intent": "check_affordability",
  "arguments": {
    "amount": "8000"
  }
}
```

### Backend

```text
AI Intent
   ↓
Backend Dispatcher
   ↓
check_affordability()
   ↓
Authoritative Financial Facts
```

### Response

The AI converts the backend facts into a natural-language response suitable for voice interaction.

```text
"You can afford the ₹8,000 headphones based on
your current available balance."
```

The **backend provides the financial facts**.

The **AI provides the explanation**.

---

## 💳 Example Payment Flow

User:

> "Send ₹5,000 to Dr Rao."

FinSight first creates a payment preview.

```text
Payment Request
      ↓
Backend Payment Preview
      ↓
User Reviews Details
      ↓
Explicit Confirmation
      ↓
Payment Execution
      ↓
Transaction Recorded
```

This ensures that a conversational request cannot accidentally become an executed payment without confirmation.

---

## 🔐 Safety Principles

### 1. Backend as Source of Truth

Financial values originate from the database and deterministic financial engine.

### 2. Explicit Payment Confirmation

Payment requests require explicit confirmation before execution.

### 3. User Isolation

Database operations are scoped to the appropriate user and account.

### 4. Deterministic Deduplication

Repeated transaction ingestion does not silently create duplicates.

### 5. Staged Document Transactions

Extracted transactions from statements require confirmation before persistence.

### 6. Decimal Monetary Arithmetic

Financial calculations use `Decimal` rather than floating-point arithmetic.

---

## 🛠️ Technology Stack

| Layer | Technology |
|---|---|
| Frontend | Web UI + Voice |
| Backend | Python |
| API | FastAPI |
| ORM | SQLAlchemy |
| Database | SQLite |
| AI | LLM-based Intent & Explanation |
| Financial Math | Python `Decimal` |
| Testing | Pytest |
| Version Control | Git |
| Deployment | Docker + AWS EC2 |

---

## ☁️ Deployment

FinSight is containerized for deployment using Docker and is designed to run on AWS EC2.

```text
AWS EC2
   │
   ▼
Ubuntu
   │
   ▼
Docker
   │
   ▼
Docker Compose
   ├── Frontend
   ├── FastAPI Backend
   ├── AI Layer
   └── Database
```

---

## 👥 Team

### FinSight

**Parth Lamba**  
**Dishita Singh**
**Harsh Vats**
**Sushant Chaudhary**

---

## ⚠️ Disclaimer

FinSight is a hackathon project and prototype.

The payment system is simulated and does not perform real-world financial transactions.

Financial insights provided by FinSight are for informational purposes and should not be considered professional financial advice.

---

<div align="center">

# 💰 FinSight

### Your finances. Your voice. Your understanding.

**Built with Python • FastAPI • SQLAlchemy • AI**

</div>
```
