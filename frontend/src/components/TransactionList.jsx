import React from 'react';

export default function TransactionList({ transactions = [] }) {
  // Take only the 5 most recent transactions for the dashboard view
  const displayTransactions = [...transactions].reverse().slice(0, 5);

  return (
    <div className="card">
      <h3 className="text-section-heading" style={{ color: 'var(--color-text-muted)', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1.5rem' }}>
        Recent Activity
      </h3>
      
      {displayTransactions.length === 0 ? (
        <p className="text-secondary" style={{ fontStyle: 'italic' }}>No recent transactions.</p>
      ) : (
        <ul style={{ listStyle: 'none', padding: 0, margin: 0, display: 'flex', flexDirection: 'column', gap: '1.5rem' }}>
          {displayTransactions.map(t => {
            const dateStr = new Date(t.transaction_date).toLocaleDateString('en-US', { day: 'numeric', month: 'short' });
            const amountStr = t.transaction_type === 'income' ? `+₹${Math.abs(t.amount)}` : `−₹${Math.abs(t.amount)}`;
            const isCredit = t.transaction_type === 'income';

            return (
              <li key={t.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                {/* Screen reader only text for full context */}
                <span className="sr-only">
                  {t.merchant_name || t.description || 'Transaction'}. {dateStr}. {t.category}. {amountStr.replace('−', 'Minus ').replace('+', 'Plus ')}.
                </span>
                
                <div aria-hidden="true">
                  <p className="text-body" style={{ fontWeight: 600 }}>{t.merchant_name || t.description || 'Transaction'}</p>
                  <p className="text-secondary" style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
                    {dateStr} · {t.category}
                  </p>
                </div>
                
                <div aria-hidden="true" className="text-body" style={{ fontWeight: 600, color: isCredit ? 'var(--color-success)' : 'var(--color-text)' }}>
                  {amountStr}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      
      <button className="btn btn-secondary" style={{ width: '100%', marginTop: '2rem' }}>
        View all transactions
      </button>
    </div>
  );
}
