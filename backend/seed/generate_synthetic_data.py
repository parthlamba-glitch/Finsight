"""
Synthetic Financial Data Generator for FinSight.

Generates a realistic, deterministic 4-month financial dataset for the demo user
spanning May 2026 through August 2026 (reference date: 2026-08-27).

Key Architecture Principles:
- Deterministic Balance: Explicit opening balance transaction (+25000.00) and
  account.balance is calculated as SUM(transaction.amount).
- Money Sign Convention:
  - Inflows (salary, refund, opening balance) are POSITIVE (+).
  - Outflows (rent, groceries, bills, shopping, subscriptions) are NEGATIVE (-).
- Deterministic Data: Fixed reference date (2026-08-27) and fixed seed.
- Food Spending Trend: Realistic month-over-month increase across May, June, July, August.
- Subscription Price Increase: Netflix recurring subscription increases from Rs 499 to Rs 699.
- Accessibility First: Mandatory default accessibility preferences for demo user.
- Re-runnable: Safely clears existing demo user data and reseeds identical dataset.
"""

import sys
import os
import random
from datetime import datetime, date
from decimal import Decimal
from typing import Dict, List, Any

# Ensure standard output can handle UTF-8 symbols on Windows consoles
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure workspace root is on sys.path for direct script execution
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.db import SessionLocal, init_db
from backend.models import User, Account, Transaction, Goal, Bill, Document, PendingPayment

# Fixed Reference Date for FinSight Synthetic Dataset
REFERENCE_DATE = date(2026, 8, 27)
DEMO_EMAIL = "aarav.sharma@example.com"


def seed_synthetic_data() -> None:
    """Populates SQLite database with rich, deterministic 4-month synthetic financial data."""
    # Seed Python's PRNG for deterministic behavior
    random.seed(42)

    init_db()
    db = SessionLocal()

    try:
        # 1. Reset Behavior: Safely clean up existing demo user data first
        existing_user = db.query(User).filter_by(email=DEMO_EMAIL).first()
        if existing_user:
            print(f"Cleaning up existing seed data for {DEMO_EMAIL}...")
            # Explicitly delete child entities to ensure clean state
            db.query(PendingPayment).filter_by(user_id=existing_user.id).delete()
            db.query(Transaction).filter_by(user_id=existing_user.id).delete()
            db.query(Bill).filter_by(user_id=existing_user.id).delete()
            db.query(Goal).filter_by(user_id=existing_user.id).delete()
            db.query(Document).filter_by(user_id=existing_user.id).delete()
            db.query(Account).filter_by(user_id=existing_user.id).delete()
            db.delete(existing_user)
            db.commit()
            print("Previous demo data cleaned up successfully.")

        print("Seeding realistic 4-month synthetic data for FinSight...")

        # 2. Create Single Demo User with Accessibility Preferences
        user = User(
            full_name="Aarav Sharma",
            email=DEMO_EMAIL,
            accessibility_prefs={
                "voice_first": True,
                "screen_reader": True,
                "spoken_confirmations": True,
                "preferred_language": "en-IN",
            },
            is_active=True,
            created_at=datetime(2026, 4, 30, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(user)
        db.flush()

        # 3. Create Account (balance will be updated to SUM(transaction.amount) after generation)
        primary_account = Account(
            user_id=user.id,
            name="HDFC Primary Savings",
            account_type="savings",
            balance=Decimal("0.00"),  # Temporary placeholder, will set authoritative sum
            monthly_income=Decimal("75000.00"),
            currency="INR",
            is_active=True,
            created_at=datetime(2026, 4, 30, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(primary_account)
        db.flush()

        # 4. Generate Deterministic Transactions (May 2026 - August 2026)
        raw_transactions_data = [
            # ==========================================
            # OPENING BALANCE & MAY 2026
            # ==========================================
            # Opening Balance
            {
                "date": datetime(2026, 4, 30, 20, 0, 0),
                "amount": Decimal("25000.00"),
                "type": "income",
                "category": "Other",
                "merchant": None,
                "desc": "Opening Balance",
            },
            # May Salary
            {
                "date": datetime(2026, 5, 1, 9, 0, 0),
                "amount": Decimal("75000.00"),
                "type": "income",
                "category": "Other",
                "merchant": "TechCorp India Pvt Ltd",
                "desc": "Monthly Salary Credit",
            },
            # May Rent
            {
                "date": datetime(2026, 5, 2, 10, 30, 0),
                "amount": Decimal("-25000.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Landlord Realty",
                "desc": "Apartment Rent Payment",
            },
            # May Food (Target: Rs 8,000 - 9,500 -> Total: Rs 8,650)
            {
                "date": datetime(2026, 5, 3, 11, 15, 0),
                "amount": Decimal("-3850.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "BigBasket",
                "desc": "Monthly Grocery Staples",
            },
            {
                "date": datetime(2026, 5, 4, 8, 45, 0),
                "amount": Decimal("-500.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Namma Metro",
                "desc": "Metro Smart Card Recharge",
            },
            {
                "date": datetime(2026, 5, 5, 20, 15, 0),
                "amount": Decimal("-480.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Dinner Delivery",
            },
            {
                "date": datetime(2026, 5, 8, 14, 0, 0),
                "amount": Decimal("-1850.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "BESCOM",
                "desc": "Electricity Utility Payment",
            },
            {
                "date": datetime(2026, 5, 9, 9, 30, 0),
                "amount": Decimal("-340.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Cab Ride to Work",
            },
            {
                "date": datetime(2026, 5, 10, 12, 0, 0),
                "amount": Decimal("-1179.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Airtel Fiber",
                "desc": "Broadband Internet Bill",
            },
            {
                "date": datetime(2026, 5, 11, 17, 30, 0),
                "amount": Decimal("-1240.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Local Grocery Store",
                "desc": "Fresh Vegetables and Dairy",
            },
            {
                "date": datetime(2026, 5, 12, 18, 45, 0),
                "amount": Decimal("-680.00"),
                "type": "expense",
                "category": "Healthcare",
                "merchant": "Apollo Pharmacy",
                "desc": "Prescription Medicines",
            },
            {
                "date": datetime(2026, 5, 14, 13, 10, 0),
                "amount": Decimal("-520.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Zomato",
                "desc": "Team Lunch Delivery",
            },
            # May Netflix Subscription (Rs 499)
            {
                "date": datetime(2026, 5, 15, 10, 0, 0),
                "amount": Decimal("-499.00"),
                "type": "expense",
                "category": "Entertainment",
                "merchant": "Netflix",
                "desc": "Monthly Netflix Subscription",
            },
            {
                "date": datetime(2026, 5, 16, 16, 20, 0),
                "amount": Decimal("-380.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Starbucks",
                "desc": "Coffee and Croissant",
            },
            {
                "date": datetime(2026, 5, 18, 15, 0, 0),
                "amount": Decimal("-2499.00"),
                "type": "expense",
                "category": "Shopping",
                "merchant": "Amazon India",
                "desc": "Wireless Noise-Canceling Headphones",
            },
            {
                "date": datetime(2026, 5, 20, 19, 10, 0),
                "amount": Decimal("-680.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Blinkit",
                "desc": "Instant Groceries & Snacks",
            },
            {
                "date": datetime(2026, 5, 22, 21, 0, 0),
                "amount": Decimal("-650.00"),
                "type": "expense",
                "category": "Entertainment",
                "merchant": "BookMyShow",
                "desc": "Weekend Movie Ticket",
            },
            {
                "date": datetime(2026, 5, 24, 20, 30, 0),
                "amount": Decimal("-620.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Dinner Bowl",
            },
            {
                "date": datetime(2026, 5, 25, 9, 15, 0),
                "amount": Decimal("-410.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Cab Ride",
            },
            {
                "date": datetime(2026, 5, 27, 18, 0, 0),
                "amount": Decimal("-880.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Nature's Basket",
                "desc": "Organic Pantry Supplies",
            },
            {
                "date": datetime(2026, 5, 28, 14, 0, 0),
                "amount": Decimal("-1500.00"),
                "type": "expense",
                "category": "Education",
                "merchant": "Coursera",
                "desc": "Machine Learning Specialization",
            },

            # ==========================================
            # JUNE 2026
            # ==========================================
            # June Salary
            {
                "date": datetime(2026, 6, 1, 9, 0, 0),
                "amount": Decimal("75000.00"),
                "type": "income",
                "category": "Other",
                "merchant": "TechCorp India Pvt Ltd",
                "desc": "Monthly Salary Credit",
            },
            # June Rent
            {
                "date": datetime(2026, 6, 2, 10, 30, 0),
                "amount": Decimal("-25000.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Landlord Realty",
                "desc": "Apartment Rent Payment",
            },
            # June Food (Target: Rs 9,500 - 11,000 -> Total: Rs 10,800)
            {
                "date": datetime(2026, 6, 3, 11, 0, 0),
                "amount": Decimal("-4200.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "BigBasket",
                "desc": "Monthly Grocery Staples",
            },
            {
                "date": datetime(2026, 6, 4, 8, 45, 0),
                "amount": Decimal("-600.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Namma Metro",
                "desc": "Metro Smart Card Recharge",
            },
            {
                "date": datetime(2026, 6, 5, 20, 0, 0),
                "amount": Decimal("-1150.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Truffles",
                "desc": "Dinner with Friends",
            },
            {
                "date": datetime(2026, 6, 7, 14, 0, 0),
                "amount": Decimal("-1980.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "BESCOM",
                "desc": "Electricity Utility Payment",
            },
            {
                "date": datetime(2026, 6, 8, 9, 20, 0),
                "amount": Decimal("-420.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Cab Ride to Office",
            },
            {
                "date": datetime(2026, 6, 9, 11, 0, 0),
                "amount": Decimal("-499.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Jio",
                "desc": "Mobile Postpaid Plan",
            },
            {
                "date": datetime(2026, 6, 10, 12, 0, 0),
                "amount": Decimal("-1179.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Airtel Fiber",
                "desc": "Broadband Internet Bill",
            },
            {
                "date": datetime(2026, 6, 11, 18, 30, 0),
                "amount": Decimal("-850.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Blinkit",
                "desc": "Quick Pantry Refill",
            },
            {
                "date": datetime(2026, 6, 13, 16, 0, 0),
                "amount": Decimal("-1800.00"),
                "type": "expense",
                "category": "Shopping",
                "merchant": "Decathlon",
                "desc": "Running Shoes and Socks",
            },
            {
                "date": datetime(2026, 6, 14, 13, 0, 0),
                "amount": Decimal("-640.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Zomato",
                "desc": "Biryani Lunch",
            },
            # June Netflix Subscription (Rs 499)
            {
                "date": datetime(2026, 6, 15, 10, 0, 0),
                "amount": Decimal("-499.00"),
                "type": "expense",
                "category": "Entertainment",
                "merchant": "Netflix",
                "desc": "Monthly Netflix Subscription",
            },
            {
                "date": datetime(2026, 6, 16, 17, 15, 0),
                "amount": Decimal("-420.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Third Wave Coffee",
                "desc": "Pour-over and Pastry",
            },
            # Occasional Refund (+850)
            {
                "date": datetime(2026, 6, 18, 14, 30, 0),
                "amount": Decimal("850.00"),
                "type": "income",
                "category": "Shopping",
                "merchant": "Amazon India",
                "desc": "Amazon Refund - Returned Item",
            },
            {
                "date": datetime(2026, 6, 19, 20, 45, 0),
                "amount": Decimal("-780.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Weekend Dinner Delivery",
            },
            {
                "date": datetime(2026, 6, 20, 11, 30, 0),
                "amount": Decimal("-950.00"),
                "type": "expense",
                "category": "Healthcare",
                "merchant": "1mg",
                "desc": "Health Supplements & Vitamins",
            },
            {
                "date": datetime(2026, 6, 22, 18, 0, 0),
                "amount": Decimal("-910.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Local Kirana Store",
                "desc": "Provisions and Spices",
            },
            {
                "date": datetime(2026, 6, 23, 15, 45, 0),
                "amount": Decimal("-750.00"),
                "type": "expense",
                "category": "Education",
                "merchant": "Bookworm Bookstore",
                "desc": "Clean Architecture Book",
            },
            {
                "date": datetime(2026, 6, 25, 20, 30, 0),
                "amount": Decimal("-1300.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Meghana Foods",
                "desc": "Family Dinner",
            },
            {
                "date": datetime(2026, 6, 26, 9, 30, 0),
                "amount": Decimal("-380.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Ola",
                "desc": "Cab Ride",
            },
            {
                "date": datetime(2026, 6, 28, 17, 0, 0),
                "amount": Decimal("-550.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "FreshMart",
                "desc": "Fresh Fruits & Veggies",
            },

            # ==========================================
            # JULY 2026
            # ==========================================
            # July Salary
            {
                "date": datetime(2026, 7, 1, 9, 0, 0),
                "amount": Decimal("75000.00"),
                "type": "income",
                "category": "Other",
                "merchant": "TechCorp India Pvt Ltd",
                "desc": "Monthly Salary Credit",
            },
            # July Rent
            {
                "date": datetime(2026, 7, 2, 10, 30, 0),
                "amount": Decimal("-25000.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Landlord Realty",
                "desc": "Apartment Rent Payment",
            },
            # July Food (Target: Rs 11,000 - 12,500 -> Total: Rs 11,850)
            {
                "date": datetime(2026, 7, 3, 11, 15, 0),
                "amount": Decimal("-4100.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "BigBasket",
                "desc": "Monthly Grocery Staples",
            },
            {
                "date": datetime(2026, 7, 4, 8, 45, 0),
                "amount": Decimal("-600.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Namma Metro",
                "desc": "Metro Smart Card Recharge",
            },
            {
                "date": datetime(2026, 7, 5, 20, 30, 0),
                "amount": Decimal("-850.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Weekend Dinner Delivery",
            },
            {
                "date": datetime(2026, 7, 7, 14, 0, 0),
                "amount": Decimal("-2150.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "BESCOM",
                "desc": "Electricity Utility Payment",
            },
            {
                "date": datetime(2026, 7, 8, 19, 0, 0),
                "amount": Decimal("-3400.00"),
                "type": "expense",
                "category": "Shopping",
                "merchant": "Myntra",
                "desc": "Formal Shirts & Trousers",
            },
            {
                "date": datetime(2026, 7, 9, 9, 15, 0),
                "amount": Decimal("-480.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Cab Ride to Client Meeting",
            },
            {
                "date": datetime(2026, 7, 10, 12, 0, 0),
                "amount": Decimal("-1179.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Airtel Fiber",
                "desc": "Broadband Internet Bill",
            },
            {
                "date": datetime(2026, 7, 11, 18, 0, 0),
                "amount": Decimal("-1100.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Blinkit",
                "desc": "Snacks and Cold Brews",
            },
            {
                "date": datetime(2026, 7, 12, 11, 30, 0),
                "amount": Decimal("-800.00"),
                "type": "expense",
                "category": "Healthcare",
                "merchant": "Practo",
                "desc": "General Health Consultation",
            },
            {
                "date": datetime(2026, 7, 13, 20, 0, 0),
                "amount": Decimal("-1600.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Toit Brewpub",
                "desc": "Dinner & Drinks with Colleagues",
            },
            # July Netflix Subscription (Price increase to Rs 699)
            {
                "date": datetime(2026, 7, 15, 10, 0, 0),
                "amount": Decimal("-699.00"),
                "type": "expense",
                "category": "Entertainment",
                "merchant": "Netflix",
                "desc": "Monthly Netflix Subscription",
            },
            {
                "date": datetime(2026, 7, 16, 16, 30, 0),
                "amount": Decimal("-450.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Starbucks",
                "desc": "Coffee and Bagel",
            },
            {
                "date": datetime(2026, 7, 18, 13, 15, 0),
                "amount": Decimal("-790.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Zomato",
                "desc": "Pasta Lunch Delivery",
            },
            {
                "date": datetime(2026, 7, 20, 15, 0, 0),
                "amount": Decimal("-1200.00"),
                "type": "expense",
                "category": "Education",
                "merchant": "Amazon India",
                "desc": "Designing Data-Intensive Applications Book",
            },
            {
                "date": datetime(2026, 7, 21, 17, 45, 0),
                "amount": Decimal("-850.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Local Supermarket",
                "desc": "Artisan Cheeses & Bread",
            },
            {
                "date": datetime(2026, 7, 23, 20, 15, 0),
                "amount": Decimal("-620.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Salad & Smoothie",
            },
            {
                "date": datetime(2026, 7, 24, 9, 30, 0),
                "amount": Decimal("-510.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Cab Ride",
            },
            {
                "date": datetime(2026, 7, 26, 19, 30, 0),
                "amount": Decimal("-740.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Truffles Cafe",
                "desc": "Burgers and Shakes",
            },
            {
                "date": datetime(2026, 7, 27, 14, 0, 0),
                "amount": Decimal("-699.00"),
                "type": "expense",
                "category": "Education",
                "merchant": "Udemy",
                "desc": "Advanced Python Mastery",
            },
            {
                "date": datetime(2026, 7, 29, 18, 30, 0),
                "amount": Decimal("-750.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "FreshToHome",
                "desc": "Fresh Fish & Poultry",
            },

            # ==========================================
            # AUGUST 2026 (Through August 27)
            # ==========================================
            # August Salary
            {
                "date": datetime(2026, 8, 1, 9, 0, 0),
                "amount": Decimal("75000.00"),
                "type": "income",
                "category": "Other",
                "merchant": "TechCorp India Pvt Ltd",
                "desc": "Monthly Salary Credit",
            },
            # August Rent
            {
                "date": datetime(2026, 8, 2, 10, 30, 0),
                "amount": Decimal("-25000.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Landlord Realty",
                "desc": "Apartment Rent Payment",
            },
            # August Food (Target: Rs 13,000 - 15,000 -> Total: Rs 14,450)
            {
                "date": datetime(2026, 8, 3, 11, 30, 0),
                "amount": Decimal("-5200.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Nature's Basket",
                "desc": "Gourmet Groceries & Imports",
            },
            {
                "date": datetime(2026, 8, 4, 8, 45, 0),
                "amount": Decimal("-700.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Namma Metro",
                "desc": "Metro Smart Card Recharge",
            },
            {
                "date": datetime(2026, 8, 5, 20, 30, 0),
                "amount": Decimal("-980.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Zomato",
                "desc": "Sushi Dinner Delivery",
            },
            {
                "date": datetime(2026, 8, 7, 14, 0, 0),
                "amount": Decimal("-1790.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "BESCOM",
                "desc": "Electricity Utility Payment",
            },
            {
                "date": datetime(2026, 8, 8, 16, 30, 0),
                "amount": Decimal("-1299.00"),
                "type": "expense",
                "category": "Shopping",
                "merchant": "Croma",
                "desc": "USB-C Multi-port Adapter & Cable",
            },
            {
                "date": datetime(2026, 8, 9, 9, 20, 0),
                "amount": Decimal("-580.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Uber India",
                "desc": "Uber Premier Ride to Tech Summit",
            },
            {
                "date": datetime(2026, 8, 10, 12, 0, 0),
                "amount": Decimal("-1179.00"),
                "type": "expense",
                "category": "Bills",
                "merchant": "Airtel Fiber",
                "desc": "Broadband Internet Bill",
            },
            {
                "date": datetime(2026, 8, 11, 18, 45, 0),
                "amount": Decimal("-1450.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Blinkit",
                "desc": "Imported Snacks & Beverages",
            },
            {
                "date": datetime(2026, 8, 12, 17, 15, 0),
                "amount": Decimal("-1120.00"),
                "type": "expense",
                "category": "Healthcare",
                "merchant": "Apollo Pharmacy",
                "desc": "Health Checkup Kit & Supplements",
            },
            {
                "date": datetime(2026, 8, 14, 20, 0, 0),
                "amount": Decimal("-2650.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Smoke House Deli",
                "desc": "Gourmet Italian Dinner",
            },
            # August Netflix Subscription (Rs 699)
            {
                "date": datetime(2026, 8, 15, 10, 0, 0),
                "amount": Decimal("-699.00"),
                "type": "expense",
                "category": "Entertainment",
                "merchant": "Netflix",
                "desc": "Monthly Netflix Subscription",
            },
            {
                "date": datetime(2026, 8, 16, 16, 0, 0),
                "amount": Decimal("-520.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Third Wave Coffee",
                "desc": "Specialty Coffee and Dessert",
            },
            {
                "date": datetime(2026, 8, 17, 20, 45, 0),
                "amount": Decimal("-1240.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Artisan Pizza Dinner",
            },
            {
                "date": datetime(2026, 8, 19, 18, 0, 0),
                "amount": Decimal("-2990.00"),
                "type": "expense",
                "category": "Shopping",
                "merchant": "Uniqlo",
                "desc": "Airism T-Shirts and Outerwear",
            },
            {
                "date": datetime(2026, 8, 20, 17, 30, 0),
                "amount": Decimal("-680.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Local Artisan Bakery",
                "desc": "Sourdough Bread and Pastries",
            },
            {
                "date": datetime(2026, 8, 22, 13, 15, 0),
                "amount": Decimal("-730.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Healthy Salad Bowl",
            },
            {
                "date": datetime(2026, 8, 23, 9, 40, 0),
                "amount": Decimal("-490.00"),
                "type": "expense",
                "category": "Transport",
                "merchant": "Ola",
                "desc": "Prime Cab Ride",
            },
            {
                "date": datetime(2026, 8, 24, 16, 30, 0),
                "amount": Decimal("-420.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Cafe Coffee Day",
                "desc": "Cold Coffee & Sandwich",
            },
            {
                "date": datetime(2026, 8, 26, 21, 0, 0),
                "amount": Decimal("-580.00"),
                "type": "expense",
                "category": "Food",
                "merchant": "Swiggy",
                "desc": "Late Night Dessert Delivery",
            },
        ]

        # Convert to ORM Transaction instances
        transactions: List[Transaction] = []
        for t_data in raw_transactions_data:
            tx = Transaction(
                account_id=primary_account.id,
                user_id=user.id,
                amount=t_data["amount"],
                currency="INR",
                transaction_type=t_data["type"],
                category=t_data["category"],
                merchant_name=t_data["merchant"],
                description=t_data["desc"],
                transaction_date=t_data["date"],
                created_at=t_data["date"],
            )
            transactions.append(tx)

        db.add_all(transactions)
        db.flush()

        # 5. Non-Negotiable: Authoritative Balance Calculation
        authoritative_balance = sum((t.amount for t in transactions), Decimal("0.00"))
        primary_account.balance = authoritative_balance
        db.flush()

        # 6. Exactly ONE Active Goal: Emergency Fund
        goal = Goal(
            user_id=user.id,
            name="Emergency Fund",
            target_amount=Decimal("150000.00"),
            current_amount=Decimal("45000.00"),
            monthly_contribution=Decimal("10000.00"),
            currency="INR",
            target_date=date(2027, 6, 30),
            status="active",
            created_at=datetime(2026, 5, 1, 10, 0, 0),
            updated_at=datetime(2026, 8, 27, 12, 0, 0),
        )
        db.add(goal)

        # 7. Exactly THREE Unpaid Upcoming Bills (Due date > 2026-08-27)
        upcoming_bills = [
            Bill(
                user_id=user.id,
                name="BESCOM Electricity",
                amount=Decimal("1850.00"),
                currency="INR",
                category="Bills",
                due_date=date(2026, 9, 5),
                frequency="monthly",
                status="unpaid",
                is_recurring=True,
                created_at=datetime(2026, 8, 20, 10, 0, 0),
                updated_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
            Bill(
                user_id=user.id,
                name="Airtel Fiber Broadband",
                amount=Decimal("1179.00"),
                currency="INR",
                category="Bills",
                due_date=date(2026, 9, 10),
                frequency="monthly",
                status="unpaid",
                is_recurring=True,
                created_at=datetime(2026, 8, 20, 10, 0, 0),
                updated_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
            Bill(
                user_id=user.id,
                name="Apartment Maintenance",
                amount=Decimal("3500.00"),
                currency="INR",
                category="Bills",
                due_date=date(2026, 9, 15),
                frequency="monthly",
                status="unpaid",
                is_recurring=True,
                created_at=datetime(2026, 8, 20, 10, 0, 0),
                updated_at=datetime(2026, 8, 20, 10, 0, 0),
            ),
        ]
        db.add_all(upcoming_bills)

        # 8. Sample Document metadata
        doc = Document(
            user_id=user.id,
            filename="bescom_electricity_bill_aug2026.pdf",
            file_path="/storage/documents/bescom_electricity_bill_aug2026.pdf",
            document_type="bill",
            mime_type="application/pdf",
            raw_text="BESCOM Electricity Bill Account: 1048291 Amount: Rs 1,850.00 Due Date: 2026-09-05",
            extracted_facts={
                "vendor": "BESCOM",
                "amount": 1850.00,
                "due_date": "2026-09-05",
                "account_number": "1048291",
            },
            is_suspicious=False,
            created_at=datetime(2026, 8, 22, 10, 0, 0),
            updated_at=datetime(2026, 8, 22, 10, 0, 0),
        )
        db.add(doc)

        # Commit transaction
        db.commit()

        # 9. Perform Comprehensive In-Database Hard Validations
        _validate_seeded_dataset(db, user.id, primary_account.id)

        # 10. Print Structured Validation Report
        _print_validation_report(db, user.id, primary_account.id)

    except Exception as e:
        db.rollback()
        print(f"CRITICAL ERROR in synthetic data generation: {e}")
        raise
    finally:
        db.close()


def _validate_seeded_dataset(db: Any, user_id: int, account_id: int) -> None:
    """
    Enforces non-negotiable hard constraints on the seeded database.
    Raises RuntimeError if any condition is violated.
    """
    # 1. Exactly one demo user
    demo_users = db.query(User).filter_by(email=DEMO_EMAIL).all()
    if len(demo_users) != 1:
        raise RuntimeError(f"Validation failed: expected 1 demo user, found {len(demo_users)}")

    user = demo_users[0]
    expected_prefs = {
        "voice_first": True,
        "screen_reader": True,
        "spoken_confirmations": True,
        "preferred_language": "en-IN",
    }
    if user.accessibility_prefs != expected_prefs:
        raise RuntimeError(f"Validation failed: invalid accessibility prefs: {user.accessibility_prefs}")

    # 2. Exactly one account
    accounts = db.query(Account).filter_by(user_id=user_id).all()
    if len(accounts) != 1:
        raise RuntimeError(f"Validation failed: expected 1 account, found {len(accounts)}")
    account = accounts[0]

    # 3. At least 60 transactions
    tx_list: List[Transaction] = (
        db.query(Transaction)
        .filter_by(account_id=account_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    if len(tx_list) < 60:
        raise RuntimeError(f"Validation failed: expected >= 60 transactions, found {len(tx_list)}")

    # 4. Transactions span approximately 4 months (May 2026 - August 2026)
    min_date = tx_list[0].transaction_date
    max_date = tx_list[-1].transaction_date
    if min_date.date() > date(2026, 5, 1) or max_date.date() > REFERENCE_DATE:
        raise RuntimeError(f"Validation failed: transaction dates {min_date} to {max_date} out of expected 4-month range")

    # 5. Salary exists for all 4 months
    salaries = [
        t for t in tx_list
        if t.category == "Other" and t.amount == Decimal("75000.00") and t.merchant_name == "TechCorp India Pvt Ltd"
    ]
    salary_months = {t.transaction_date.month for t in salaries if t.transaction_date.year == 2026}
    if salary_months != {5, 6, 7, 8}:
        raise RuntimeError(f"Validation failed: salary not found in all 4 months {salary_months}")

    # 6. Food spending exists in all 4 months and strictly increases
    food_by_month: Dict[int, Decimal] = {5: Decimal("0.00"), 6: Decimal("0.00"), 7: Decimal("0.00"), 8: Decimal("0.00")}
    for t in tx_list:
        if t.category == "Food" and t.transaction_date.year == 2026 and t.transaction_date.month in food_by_month:
            # Food expenses are negative amounts
            food_by_month[t.transaction_date.month] += abs(t.amount)

    for m, total in food_by_month.items():
        if total <= Decimal("0.00"):
            raise RuntimeError(f"Validation failed: no food spending in month {m}")

    if not (food_by_month[5] < food_by_month[6] < food_by_month[7] < food_by_month[8]):
        raise RuntimeError(
            f"Validation failed: food spending must strictly increase across months: {food_by_month}"
        )

    # 7. Subscription exists in all 4 months and changes from 499 to 699
    netflix_txs = [
        t for t in tx_list
        if t.category == "Entertainment" and t.merchant_name == "Netflix"
    ]
    netflix_by_month: Dict[int, Decimal] = {}
    for t in netflix_txs:
        if t.transaction_date.year == 2026:
            netflix_by_month[t.transaction_date.month] = t.amount

    if set(netflix_by_month.keys()) != {5, 6, 7, 8}:
        raise RuntimeError(f"Validation failed: Netflix subscription missing in some months: {netflix_by_month}")

    if netflix_by_month[5] != Decimal("-499.00") or netflix_by_month[6] != Decimal("-499.00"):
        raise RuntimeError(f"Validation failed: Netflix May/June amount must be -499.00, got: {netflix_by_month}")

    if netflix_by_month[7] != Decimal("-699.00") or netflix_by_month[8] != Decimal("-699.00"):
        raise RuntimeError(f"Validation failed: Netflix July/August amount must be -699.00, got: {netflix_by_month}")

    # 8. Recurring bills exist
    rent_txs = [t for t in tx_list if t.category == "Bills" and t.amount == Decimal("-25000.00")]
    if len(rent_txs) != 4:
        raise RuntimeError(f"Validation failed: expected 4 rent transactions (-25000.00), found {len(rent_txs)}")

    # 9. Exactly one active goal (Emergency Fund)
    goals = db.query(Goal).filter_by(user_id=user_id, status="active").all()
    if len(goals) != 1 or goals[0].name != "Emergency Fund":
        raise RuntimeError(f"Validation failed: expected 1 active Emergency Fund goal, found {goals}")

    # 10. Exactly three upcoming unpaid bills with due dates after reference date
    upcoming = db.query(Bill).filter_by(user_id=user_id, status="unpaid").all()
    if len(upcoming) != 3:
        raise RuntimeError(f"Validation failed: expected 3 upcoming bills, found {len(upcoming)}")
    for b in upcoming:
        if b.due_date <= REFERENCE_DATE:
            raise RuntimeError(f"Validation failed: upcoming bill {b.name} due date {b.due_date} <= reference date {REFERENCE_DATE}")

    # 11. Authoritative balance equals cached account balance
    authoritative_balance = sum((t.amount for t in tx_list), Decimal("0.00"))
    if account.balance != authoritative_balance:
        raise RuntimeError(
            f"Validation failed: account.balance ({account.balance}) != authoritative_balance ({authoritative_balance})"
        )


def _print_validation_report(db: Any, user_id: int, account_id: int) -> None:
    """Prints the formatted validation report as required by FinSight specifications."""
    user = db.query(User).filter_by(id=user_id).first()
    account = db.query(Account).filter_by(id=account_id).first()
    tx_list: List[Transaction] = (
        db.query(Transaction)
        .filter_by(account_id=account_id)
        .order_by(Transaction.transaction_date.asc())
        .all()
    )
    goals = db.query(Goal).filter_by(user_id=user_id).all()
    bills = db.query(Bill).filter_by(user_id=user_id).all()

    month_names = {5: "May 2026", 6: "June 2026", 7: "July 2026", 8: "August 2026"}

    # Monthly counts, income, spending
    tx_counts_by_month: Dict[int, int] = {5: 0, 6: 0, 7: 0, 8: 0}
    income_by_month: Dict[int, Decimal] = {5: Decimal("0.00"), 6: Decimal("0.00"), 7: Decimal("0.00"), 8: Decimal("0.00")}
    spending_by_month: Dict[int, Decimal] = {5: Decimal("0.00"), 6: Decimal("0.00"), 7: Decimal("0.00"), 8: Decimal("0.00")}
    food_by_month: Dict[int, Decimal] = {5: Decimal("0.00"), 6: Decimal("0.00"), 7: Decimal("0.00"), 8: Decimal("0.00")}
    category_totals: Dict[str, Decimal] = {}

    for t in tx_list:
        m = t.transaction_date.month
        # Group opening balance on April 30 into May for display count/income
        display_m = 5 if (t.transaction_date.year == 2026 and m == 4) else m

        if display_m in tx_counts_by_month:
            tx_counts_by_month[display_m] += 1
            if t.amount > Decimal("0.00"):
                income_by_month[display_m] += t.amount
            else:
                spending_by_month[display_m] += abs(t.amount)

        if t.category == "Food" and display_m in food_by_month:
            food_by_month[display_m] += abs(t.amount)

        category_totals[t.category] = category_totals.get(t.category, Decimal("0.00")) + t.amount

    netflix_payments = [
        f"{month_names[t.transaction_date.month]}: ₹{abs(t.amount)}"
        for t in tx_list if t.merchant_name == "Netflix"
    ]

    authoritative_balance = sum((t.amount for t in tx_list), Decimal("0.00"))
    balances_match = (account.balance == authoritative_balance)

    print("\n=== FINSIGHT SEED VALIDATION ===")
    print(f"\nUser:\n{user.full_name} ({user.email}) [Voice-First: {user.accessibility_prefs.get('voice_first')}]")
    print(f"\nTransaction count:\n{len(tx_list)}")
    print(f"\nDate range:\n{tx_list[0].transaction_date.strftime('%Y-%m-%d')} to {tx_list[-1].transaction_date.strftime('%Y-%m-%d')}")

    print("\nMonthly transaction counts:")
    for m in [5, 6, 7, 8]:
        print(f"  {month_names[m]}: {tx_counts_by_month[m]} transactions")

    print("\nMonthly income:")
    for m in [5, 6, 7, 8]:
        print(f"  {month_names[m]}: ₹{income_by_month[m]:,.2f}")

    print("\nMonthly spending:")
    for m in [5, 6, 7, 8]:
        print(f"  {month_names[m]}: ₹{spending_by_month[m]:,.2f}")

    print("\nFood spending by month:")
    for m in [5, 6, 7, 8]:
        print(f"  {month_names[m]}: ₹{food_by_month[m]:,.2f}")

    print("\nSubscription payments:")
    for p in netflix_payments:
        print(f"  Netflix: {p}")

    print("\nCategory totals:")
    for cat, total in sorted(category_totals.items()):
        print(f"  {cat}: ₹{total:,.2f}")

    print("\nUpcoming bills:")
    for b in bills:
        print(f"  {b.name}: ₹{b.amount:,.2f} (Due: {b.due_date}, Status: {b.status})")

    print("\nGoal:")
    for g in goals:
        print(f"  {g.name}: Target ₹{g.target_amount:,.2f}, Current ₹{g.current_amount:,.2f}, Monthly ₹{g.monthly_contribution:,.2f} (Status: {g.status})")

    print(f"\nAuthoritative balance:\n₹{authoritative_balance:,.2f}")
    print(f"\nCached account balance:\n₹{account.balance:,.2f}")
    print(f"\nBalances match:\n{'TRUE' if balances_match else 'FALSE'}\n")


if __name__ == "__main__":
    seed_synthetic_data()
