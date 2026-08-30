import React from 'react';

export default function AuthModal({
  isOpen,
  paymentDetails,
  onConfirm,
  onCancel,
  isExecuting = false,
}) {
  if (!isOpen) return null;

  const recipient = paymentDetails?.recipient_name || 'Recipient';
  const amount = paymentDetails?.amount !== undefined ? Number(paymentDetails.amount).toLocaleString('en-IN') : '0';
  const balanceAfter = paymentDetails?.balance_after !== undefined ? Number(paymentDetails.balance_after).toLocaleString('en-IN') : null;
  const isHighRisk = paymentDetails?.risk_level === 'high' || paymentDetails?.fraud_warning;

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        backgroundColor: 'rgba(0,0,0,0.85)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 9999,
        padding: '1rem',
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-title"
      aria-describedby="auth-desc"
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '440px',
          textAlign: 'center',
          border: isHighRisk ? '2px solid var(--color-warning)' : '2px solid var(--color-primary)',
          boxShadow: '0 8px 32px rgba(0,0,0,0.5)',
        }}
      >
        <h2
          id="auth-title"
          className="text-page-heading"
          style={{
            marginBottom: '0.75rem',
            color: isHighRisk ? 'var(--color-warning)' : 'var(--color-primary)',
          }}
        >
          {isHighRisk ? '⚠️ Authorize High-Risk Payment' : 'Confirm Payment'}
        </h2>

        <p id="auth-desc" className="text-body" style={{ marginBottom: '1.25rem' }}>
          Please review the payment details before authorizing this transaction.
        </p>

        {/* AUTHORITATIVE STAGED SUMMARY */}
        <div
          style={{
            backgroundColor: 'var(--color-bg)',
            borderRadius: '8px',
            padding: '1rem',
            marginBottom: '1.5rem',
            textAlign: 'left',
          }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span className="text-secondary">Recipient:</span>
            <span className="text-body" style={{ fontWeight: 600 }}>
              {recipient}
            </span>
          </div>

          <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
            <span className="text-secondary">Amount:</span>
            <span className="text-body" style={{ fontWeight: 700, color: 'var(--color-primary)', fontSize: '1.1rem' }}>
              ₹{amount}
            </span>
          </div>

          {balanceAfter !== null && (
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
              <span className="text-secondary">Balance After:</span>
              <span className="text-body">₹{balanceAfter}</span>
            </div>
          )}

          {isHighRisk && paymentDetails?.risk_reasons && paymentDetails.risk_reasons.length > 0 && (
            <div
              style={{
                marginTop: '0.75rem',
                paddingTop: '0.75rem',
                borderTop: '1px solid var(--color-border)',
              }}
            >
              <p className="text-secondary" style={{ color: 'var(--color-warning)', fontWeight: 600, fontSize: '0.85rem' }}>
                Risk Factors Detected:
              </p>
              <ul style={{ paddingLeft: '1.25rem', margin: '0.25rem 0 0 0', fontSize: '0.85rem' }}>
                {paymentDetails.risk_reasons.map((reason, idx) => (
                  <li key={idx} className="text-secondary">
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* ACTIONS */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
          <button
            className="btn"
            style={{
              padding: '14px',
              fontSize: '1.1rem',
              backgroundColor: isHighRisk ? 'var(--color-warning)' : 'var(--color-primary)',
              color: 'var(--color-bg)',
              fontWeight: 600,
            }}
            onClick={onConfirm}
            disabled={isExecuting}
          >
            {isExecuting ? 'Authorizing...' : 'Authorize & Send Payment'}
          </button>

          <button
            className="btn btn-secondary"
            style={{ padding: '12px' }}
            onClick={onCancel}
            disabled={isExecuting}
          >
            Cancel Payment
          </button>
        </div>
      </div>
    </div>
  );
}
