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
  Briefcase,
} from 'lucide-react';
import StatusBadge from './StatusBadge';

/**
 * Helper to resolve merchant & category iconography
 */
function getCategoryIcon(category, isCredit) {
  if (isCredit) return <ArrowDownLeft size={18} color="var(--fs-accent)" />;

  switch (category?.toLowerCase()) {
    case 'food':
    case 'dining':
      return <Utensils size={18} />;
    case 'transport':
    case 'travel':
      return <Car size={18} />;
    case 'shopping':
    case 'groceries':
      return <ShoppingBag size={18} />;
    case 'bills':
    case 'utilities':
      return <Receipt size={18} />;
    case 'entertainment':
      return <Film size={18} />;
    case 'healthcare':
    case 'health':
      return <HeartPulse size={18} />;
    case 'education':
      return <GraduationCap size={18} />;
    case 'salary':
    case 'income':
      return <Briefcase size={18} />;
    default:
      return <ArrowUpRight size={18} />;
  }
}

/**
 * TransactionList Component
 * Premium financial ledger with category iconography, tabular numerals,
 * and accessible screen-reader descriptions.
 *
 * NON-NEGOTIABLE RULE:
 * Strictly displays backend-provided transaction facts without calculating balances or totals.
 */
export default function TransactionList({ transactions = [] }) {
  // Show up to 8 most recent transactions in reverse chronological order
  const displayTransactions = [...transactions].reverse().slice(0, 8);

  if (displayTransactions.length === 0) {
    return (
      <div className="ledger-container" style={{ textAlign: 'center', padding: '3rem 1.5rem' }}>
        <CircleDollarSign size={40} color="var(--fs-text-muted)" style={{ marginBottom: '1rem' }} aria-hidden="true" />
        <h3 className="text-card-heading" style={{ color: 'var(--fs-text)', marginBottom: '0.5rem' }}>
          No Transactions Recorded Yet
        </h3>
        <p className="text-secondary" style={{ fontStyle: 'italic', margin: 0, maxWidth: '420px', marginInline: 'auto' }}>
          Connect your live bank feed or scan a bank statement above to import your financial ledger.
        </p>
      </div>
    );
  }

  return (
    <div className="ledger-container" aria-labelledby="ledger-title">
      {/* Ledger Header */}
      <div className="ledger-header">
        <div>
          <h2 id="ledger-title" className="text-card-heading" style={{ color: 'var(--fs-text)', margin: 0 }}>
            Recent Transactions
          </h2>
          <span className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
            Authoritative Account Ledger
          </span>
        </div>

        <StatusBadge variant="neutral">
          Showing Last {displayTransactions.length} Entries
        </StatusBadge>
      </div>

      {/* Ledger Table Rows */}
      <div role="table" aria-label="Recent Account Transactions" className="flex-col">
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
            <div
              key={t.id || idx}
              role="row"
              className="ledger-row"
            >
              {/* Accessible description for screen readers */}
              <span className="sr-only">
                {merchantTitle}. Date: {dateStr}. Category: {categoryName}. Amount: {isCredit ? 'Credit of ' : 'Debit of '}{absVal} rupees.
              </span>

              {/* Left Column: Merchant Icon & Meta */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }} aria-hidden="true">
                <div
                  className="ledger-merchant-icon"
                  style={{
                    backgroundColor: isCredit
                      ? 'var(--fs-success-surface)'
                      : 'var(--fs-surface-elevated)',
                    color: isCredit ? 'var(--fs-accent)' : 'var(--fs-text-secondary)',
                  }}
                >
                  {getCategoryIcon(categoryName, isCredit)}
                </div>

                <div>
                  <p
                    className="text-body"
                    style={{
                      fontWeight: 600,
                      color: 'var(--fs-text)',
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
                    <span style={{ color: 'var(--fs-border-hover)' }}>•</span>
                    <span className="text-meta" style={{ color: 'var(--fs-text-muted)' }}>
                      {categoryName}
                    </span>
                  </div>
                </div>
              </div>

              {/* Right Column: Signed Monetary Amount */}
              <div
                aria-hidden="true"
                className="tabular-nums"
                style={{
                  fontWeight: 700,
                  fontSize: '1.05rem',
                  color: isCredit ? 'var(--fs-accent)' : 'var(--fs-text)',
                  textAlign: 'right',
                  whiteSpace: 'nowrap',
                }}
              >
                {amountDisplay}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
