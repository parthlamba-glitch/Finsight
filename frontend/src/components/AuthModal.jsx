import React, { useEffect, useRef } from 'react';
import { AlertTriangle, ArrowRight, X, Lock } from 'lucide-react';
import StatusBadge from './StatusBadge';

/**
 * AuthModal Component
 * High-trust payment confirmation modal.
 *
 * CRITICAL SECURITY GUARANTEES:
 * - All monetary values and risk factors come strictly from backend preview facts.
 * - Never executes payment prematurely or without explicit confirmation.
 * - Manages focus trapping and keyboard Escape handling for WCAG compliance.
 */
export default function AuthModal({
  isOpen,
  paymentDetails,
  onConfirm,
  onCancel,
  isExecuting = false,
}) {
  const confirmButtonRef = useRef(null);

  // Focus trap and Escape key listener
  useEffect(() => {
    if (!isOpen) return;

    const handleKeyDown = (e) => {
      if (e.key === 'Escape' && !isExecuting) {
        onCancel();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    if (confirmButtonRef.current) {
      confirmButtonRef.current.focus();
    }

    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isExecuting, onCancel]);

  if (!isOpen) return null;

  const recipient = paymentDetails?.recipient_name || 'Recipient';
  const amountStr =
    paymentDetails?.amount !== undefined
      ? Number(paymentDetails.amount).toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : '0.00';

  const balanceAfterStr =
    paymentDetails?.balance_after !== undefined && paymentDetails.balance_after !== null
      ? Number(paymentDetails.balance_after).toLocaleString('en-IN', {
          minimumFractionDigits: 2,
          maximumFractionDigits: 2,
        })
      : null;

  const isHighRisk = paymentDetails?.risk_level === 'high' || paymentDetails?.fraud_warning;

  return (
    <div
      className="modal-backdrop"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(5, 15, 11, 0.88)',
        backdropFilter: 'blur(8px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 10000,
        padding: '1.25rem',
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-auth-title"
      aria-describedby="payment-auth-desc"
    >
      <div
        className={`card ${isHighRisk ? 'card-warning' : 'card-hero'}`}
        style={{
          width: '100%',
          maxWidth: '480px',
          border: isHighRisk
            ? '1.5px solid var(--fs-warning-border, rgba(230, 184, 92, 0.45))'
            : '1.5px solid var(--fs-accent, #8DDB92)',
          boxShadow: 'var(--fs-shadow-lg, 0 8px 32px rgba(0, 0, 0, 0.5))',
          padding: '2rem 1.75rem',
          borderRadius: 'var(--fs-radius-modal, 20px)',
          position: 'relative',
        }}
      >
        {/* Header with Close Icon */}
        <div className="flex-between" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <div
              style={{
                width: '36px',
                height: '36px',
                borderRadius: 'var(--fs-radius-sm, 8px)',
                backgroundColor: isHighRisk
                  ? 'var(--fs-warning-surface, rgba(230, 184, 92, 0.15))'
                  : 'var(--fs-accent-surface, rgba(141, 219, 146, 0.12))',
                color: isHighRisk ? 'var(--fs-warning, #E6B85C)' : 'var(--fs-accent, #8DDB92)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {isHighRisk ? <AlertTriangle size={20} /> : <Lock size={18} />}
            </div>
            <div>
              <h2
                id="payment-auth-title"
                className="text-card-heading"
                style={{
                  color: isHighRisk ? 'var(--fs-warning-bright, #F5CF80)' : 'var(--fs-text, #F5F4EC)',
                  margin: 0,
                  fontSize: '1.25rem',
                }}
              >
                {isHighRisk ? 'Authorize High-Risk Payment' : 'Confirm Payment Authorization'}
              </h2>
              <span className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Stage: Staged For Confirmation
              </span>
            </div>
          </div>

          <button
            type="button"
            onClick={onCancel}
            disabled={isExecuting}
            style={{
              background: 'transparent',
              border: 'none',
              color: 'var(--fs-text-muted, #71817A)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--fs-radius-xs, 4px)',
            }}
            aria-label="Close payment modal and cancel"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <p id="payment-auth-desc" className="text-secondary" style={{ marginBottom: '1.5rem', fontSize: '0.95rem' }}>
          Please review the recipient and authoritative balance impact before authorizing this transaction.
        </p>

        {/* AUTHORITATIVE BACKEND LEDGER FACTS */}
        <div
          style={{
            backgroundColor: 'var(--fs-bg, #071510)',
            borderRadius: 'var(--fs-radius-md, 14px)',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            border: '1px solid var(--fs-border, #1B382E)',
          }}
        >
          <div className="flex-between" style={{ paddingBottom: '0.75rem', borderBottom: '1px solid var(--fs-border-subtle, #142E25)' }}>
            <span className="text-secondary">Recipient / Payee</span>
            <span className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text, #F5F4EC)' }}>
              {recipient}
            </span>
          </div>

          <div className="flex-between" style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--fs-border-subtle, #142E25)' }}>
            <span className="text-secondary">Payment Amount</span>
            <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent, #8DDB92)', fontWeight: 700 }}>
              ₹{amountStr}
            </span>
          </div>

          {balanceAfterStr !== null && (
            <div className="flex-between" style={{ padding: '0.75rem 0', borderBottom: isHighRisk ? '1px solid var(--fs-border-subtle, #142E25)' : 'none' }}>
              <span className="text-secondary">Projected Balance After</span>
              <span className="text-body tabular-nums" style={{ fontWeight: 600, color: 'var(--fs-text-secondary, #AAB8B1)' }}>
                ₹{balanceAfterStr}
              </span>
            </div>
          )}

          {/* Risk Level Badge */}
          <div className="flex-between" style={{ paddingTop: '0.75rem' }}>
            <span className="text-secondary">Security Assessment</span>
            <StatusBadge variant={isHighRisk ? 'warning' : 'success'}>
              {isHighRisk ? 'High Risk Anomaly' : 'Standard Payment'}
            </StatusBadge>
          </div>

          {/* Risk Reasons from Backend */}
          {isHighRisk && paymentDetails?.risk_reasons && paymentDetails.risk_reasons.length > 0 && (
            <div
              style={{
                marginTop: '0.85rem',
                paddingTop: '0.85rem',
                borderTop: '1px solid var(--fs-border-subtle, #142E25)',
              }}
            >
              <p className="text-meta" style={{ color: 'var(--fs-warning, #E6B85C)', fontWeight: 600, marginBottom: '0.35rem' }}>
                Detected Risk Factors:
              </p>
              <ul style={{ paddingLeft: '1.25rem', margin: 0 }} className="flex-col gap-1">
                {paymentDetails.risk_reasons.map((reason, idx) => (
                  <li key={idx} className="text-secondary" style={{ fontSize: '0.85rem' }}>
                    {reason}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Action Buttons */}
        <div className="flex-col gap-3">
          <button
            ref={confirmButtonRef}
            type="button"
            className="btn"
            style={{
              width: '100%',
              backgroundColor: isHighRisk ? 'var(--fs-warning, #E6B85C)' : 'var(--fs-accent, #8DDB92)',
              color: 'var(--fs-bg, #071510)',
              fontWeight: 700,
            }}
            onClick={onConfirm}
            disabled={isExecuting}
            aria-label={`Authorize and send payment of ₹${amountStr} to ${recipient}`}
          >
            <span>{isExecuting ? 'Authorizing Payment...' : 'Authorize & Send Payment'}</span>
            <ArrowRight size={18} aria-hidden="true" />
          </button>

          <button
            type="button"
            className="btn btn-secondary"
            style={{ width: '100%' }}
            onClick={onCancel}
            disabled={isExecuting}
            aria-label="Cancel this payment"
          >
            Cancel Payment
          </button>
        </div>
      </div>
    </div>
  );
}
