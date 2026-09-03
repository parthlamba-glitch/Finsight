import React from 'react';
import {
  Utensils,
  Car,
  ShoppingBag,
  Receipt,
  Film,
  HeartPulse,
  GraduationCap,
  ArrowDownLeft,
  ArrowUpRight,
  CircleDollarSign,
} from 'lucide-react';
import StatusBadge from './StatusBadge';

/**
 * Helper to resolve category iconography
 */
function getCategoryIcon(category, isCredit) {
  if (isCredit) return <ArrowDownLeft size={16} />;

  switch (category?.toLowerCase()) {
    case 'food':
      return <Utensils size={16} />;
    case 'transport':
      return <Car size={16} />;
    case 'shopping':
      return <ShoppingBag size={16} />;
    case 'bills':
      return <Receipt size={16} />;
    case 'entertainment':
      return <Film size={16} />;
    case 'healthcare':
      return <HeartPulse size={16} />;
    case 'education':
      return <GraduationCap size={16} />;
    default:
      return <ArrowUpRight size={16} />;
  }
}

/**
 * TransactionList Component
 * Renders a clean, high-contrast financial ledger.
 *
 * NON-NEGOTIABLE RULE:
 * Strictly displays backend-provided monetary values without computing balances or totals.
 */
export default function TransactionList({ transactions = [] }) {
  // Show up to 8 most recent transactions in reverse chronological order
  const displayTransactions = [...transactions].reverse().slice(0, 8);

  if (displayTransactions.length === 0) {
    return (
      <div
        className="card"
        style={{
          textAlign: 'center',
          padding: '2.5rem 1.5rem',
          backgroundColor: 'var(--fs-surface-card, #0F251E)',
        }}
      >
        <CircleDollarSign size={36} color="var(--fs-text-muted, #71817A)" style={{ marginBottom: '0.75rem' }} aria-hidden="true" />
        <h3 className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', marginBottom: '0.5rem' }}>
          No Transactions Yet
        </h3>
        <p className="text-secondary" style={{ fontStyle: 'italic', margin: 0 }}>
          Synchronize your bank feed or scan a bank statement to import your latest activity.
        </p>
      </div>
    );
  }

  return (
    <div className="card" style={{ padding: '1.25rem 1.5rem' }}>
      <ul
        style={{
          listStyle: 'none',
          padding: 0,
          margin: 0,
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {displayTransactions.map((t, idx) => {
          const dateObj = new Date(t.transaction_date);
          const dateStr = dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
          const isCredit = t.transaction_type === 'income' || Number(t.amount) > 0;
          const absVal = Math.abs(Number(t.amount)).toLocaleString('en-IN', {
            minimumFractionDigits: 2,
            maximumFractionDigits: 2,
          });
          const amountDisplay = isCredit ? `+₹${absVal}` : `−₹${absVal}`;
          const merchantTitle = t.merchant_name || t.description || 'Transaction';
          const categoryName = t.category || 'General';

          return (
            <li
              key={t.id || idx}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '1rem 0',
                borderBottom: idx !== displayTransactions.length - 1 ? '1px solid var(--fs-border-subtle, #142E25)' : 'none',
                gap: '1rem',
              }}
            >
              {/* Full context accessible text for screen readers */}
              <span className="sr-only">
                {merchantTitle}. {dateStr}. Category: {categoryName}. Amount: {isCredit ? 'Plus ' : 'Minus '}{absVal} rupees.
              </span>

              {/* Left Item Details */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '0.85rem' }} aria-hidden="true">
                <div
                  style={{
                    width: '40px',
                    height: '40px',
                    borderRadius: 'var(--fs-radius-md, 14px)',
                    backgroundColor: isCredit
                      ? 'var(--fs-success-surface, rgba(141, 219, 146, 0.12))'
                      : 'var(--fs-surface-elevated, #132D24)',
                    color: isCredit ? 'var(--fs-success, #8DDB92)' : 'var(--fs-text-secondary, #AAB8B1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                    border: '1px solid var(--fs-border-subtle, #142E25)',
                  }}
                >
                  {getCategoryIcon(categoryName, isCredit)}
                </div>

                <div>
                  <p
                    className="text-body"
                    style={{
                      fontWeight: 600,
                      color: 'var(--fs-text, #F5F4EC)',
                      margin: 0,
                      fontSize: '0.975rem',
                    }}
                  >
                    {merchantTitle}
                  </p>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginTop: '0.2rem' }}>
                    <span className="text-secondary" style={{ fontSize: '0.825rem' }}>
                      {dateStr}
                    </span>
                    <span style={{ color: 'var(--fs-border, #1B382E)' }}>•</span>
                    <StatusBadge variant="neutral" showDot={false}>
                      {categoryName}
                    </StatusBadge>
                  </div>
                </div>
              </div>

              {/* Right Monetary Amount */}
              <div
                aria-hidden="true"
                className="tabular-nums"
                style={{
                  fontWeight: 700,
                  fontSize: '1rem',
                  color: isCredit ? 'var(--fs-accent, #8DDB92)' : 'var(--fs-text, #F5F4EC)',
                  textAlign: 'right',
                  whiteSpace: 'nowrap',
                }}
              >
                {amountDisplay}
              </div>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
