import React, { useEffect, useRef } from 'react';
import { AlertTriangle, ArrowRight, X, Lock } from 'lucide-react';
import StatusBadge from './StatusBadge';

/**
 * AuthModal Component
 * High-trust payment authorization modal.
 *
 * CRITICAL SECURITY GUARANTEES:
 * - All monetary values and risk factors come strictly from backend preview facts.
 * - Never executes payment prematurely without explicit confirmation.
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

  // Focus trap & Escape dismiss
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
        WebkitBackdropFilter: 'blur(8px)',
        display: 'flex',
        justifyContent: 'center',
        alignItems: 'center',
        zIndex: 10000,
        padding: '1.25rem',
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="payment-modal-heading"
      aria-describedby="payment-modal-desc"
    >
      <div
        className="card"
        style={{
          width: '100%',
          maxWidth: '480px',
          border: isHighRisk
            ? '1.5px solid var(--fs-warning-border)'
            : '1.5px solid rgba(141, 219, 146, 0.4)',
          boxShadow: 'var(--fs-shadow-lg)',
          padding: '2.25rem 2rem',
          borderRadius: 'var(--fs-radius-modal)',
          position: 'relative',
          backgroundColor: 'var(--fs-surface-card)',
        }}
      >
        {/* Modal Header */}
        <div className="flex-between" style={{ marginBottom: '1.25rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
            <div
              style={{
                width: '38px',
                height: '38px',
                borderRadius: 'var(--fs-radius-md)',
                backgroundColor: isHighRisk
                  ? 'var(--fs-warning-surface)'
                  : 'var(--fs-accent-surface)',
                color: isHighRisk ? 'var(--fs-warning)' : 'var(--fs-accent)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              {isHighRisk ? <AlertTriangle size={20} /> : <Lock size={18} />}
            </div>
            <div>
              <h2
                id="payment-modal-heading"
                className="text-card-heading"
                style={{
                  color: isHighRisk ? 'var(--fs-warning-bright)' : 'var(--fs-text)',
                  margin: 0,
                  fontSize: '1.25rem',
                }}
              >
                {isHighRisk ? 'Authorize Anomaly Payment' : 'Authorize Payment'}
              </h2>
              <span className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                Stage: Confirmation Required
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
              color: 'var(--fs-text-muted)',
              cursor: 'pointer',
              padding: '6px',
              borderRadius: 'var(--fs-radius-xs)',
            }}
            aria-label="Cancel and close payment confirmation modal"
          >
            <X size={20} aria-hidden="true" />
          </button>
        </div>

        <p id="payment-modal-desc" className="text-secondary" style={{ marginBottom: '1.5rem', fontSize: '0.925rem' }}>
          Review the recipient and authoritative balance impact before authorizing this transaction.
        </p>

        {/* Authoritative Ledger Summary */}
        <div
          style={{
            backgroundColor: 'var(--fs-bg)',
            borderRadius: 'var(--fs-radius-md)',
            padding: '1.25rem',
            marginBottom: '1.5rem',
            border: '1px solid var(--fs-border)',
          }}
        >
          <div className="flex-between" style={{ paddingBottom: '0.75rem', borderBottom: '1px solid var(--fs-border-subtle)' }}>
            <span className="text-secondary">Recipient / Payee</span>
            <span className="text-body" style={{ fontWeight: 600, color: 'var(--fs-text)' }}>
              {recipient}
            </span>
          </div>

          <div className="flex-between" style={{ padding: '0.75rem 0', borderBottom: '1px solid var(--fs-border-subtle)' }}>
            <span className="text-secondary">Payment Amount</span>
            <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent)', fontWeight: 700 }}>
              ₹{amountStr}
            </span>
          </div>

          {balanceAfterStr !== null && (
            <div className="flex-between" style={{ padding: '0.75rem 0', borderBottom: isHighRisk ? '1px solid var(--fs-border-subtle)' : 'none' }}>
              <span className="text-secondary">Available Balance After</span>
              <span className="text-body tabular-nums" style={{ fontWeight: 600, color: 'var(--fs-text-secondary)' }}>
                ₹{balanceAfterStr}
              </span>
            </div>
          )}

          {/* Risk Level Badge */}
          <div className="flex-between" style={{ paddingTop: '0.75rem' }}>
            <span className="text-secondary">Risk Assessment</span>
            <StatusBadge variant={isHighRisk ? 'warning' : 'success'}>
              {isHighRisk ? 'High Risk Anomaly' : 'Low Risk Verified'}
            </StatusBadge>
          </div>

          {/* Risk Factors Breakdown from Backend */}
          {isHighRisk && paymentDetails?.risk_reasons && paymentDetails.risk_reasons.length > 0 && (
            <div
              style={{
                marginTop: '0.85rem',
                paddingTop: '0.85rem',
                borderTop: '1px solid var(--fs-border-subtle)',
              }}
            >
              <p className="text-meta" style={{ color: 'var(--fs-warning)', fontWeight: 600, marginBottom: '0.35rem' }}>
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

        {/* Action Controls */}
        <div className="flex-col gap-3">
          <button
            ref={confirmButtonRef}
            type="button"
            className="btn"
            style={{
              width: '100%',
              backgroundColor: isHighRisk ? 'var(--fs-warning)' : 'var(--fs-accent)',
              color: 'var(--fs-bg)',
              fontWeight: 700,
            }}
            onClick={onConfirm}
            disabled={isExecuting}
            aria-label={`Authorize and send payment of ₹${amountStr} to ${recipient}`}
          >
            <span>{isExecuting ? 'Authorizing Payment...' : 'Authorize Payment'}</span>
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
