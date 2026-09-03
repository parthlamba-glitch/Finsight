import React, { useState } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, RotateCcw, Search, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from './StatusBadge';

/**
 * ScamChecker Component
 * FinSight's PROTECT Pillar interface for evaluating suspicious SMS, email,
 * and payment messages for scam patterns and fraud indicators.
 */
export default function ScamChecker({ onAnnounce }) {
  const [messageInput, setMessageInput] = useState('');
  const [result, setResult] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleCheck = async (textToCheck = null) => {
    const text = textToCheck || messageInput;
    if (!text || !text.trim()) {
      const emptyMsg = 'Please paste or enter the message you want to evaluate.';
      setErrorMsg(emptyMsg);
      if (onAnnounce) onAnnounce(emptyMsg);
      return;
    }

    setIsChecking(true);
    setErrorMsg('');
    if (onAnnounce) onAnnounce('Analyzing message for fraud and security indicators...');

    try {
      const assessment = await api.checkScam(text);
      setResult(assessment);
      if (onAnnounce && assessment.answer_text) {
        onAnnounce(assessment.answer_text);
      }
    } catch (err) {
      const failMsg = err.message || 'Failed to analyze message.';
      setErrorMsg(failMsg);
      if (onAnnounce) onAnnounce(failMsg);
    } finally {
      setIsChecking(false);
    }
  };

  const reset = () => {
    setResult(null);
    setMessageInput('');
    setErrorMsg('');
  };

  const handleSampleMessage = () => {
    const sample =
      'URGENT: Your HDFC Bank account will be blocked within 24 hours due to pending KYC. Click http://bit.ly/hdfc-kyc-verify to update immediately.';
    setMessageInput(sample);
    handleCheck(sample);
  };

  const isHighRisk = result?.risk_level === 'high' || result?.looks_suspicious;
  const isMediumRisk = result?.risk_level === 'medium';

  return (
    <div
      className={`card ${isHighRisk ? 'card-danger' : ''}`}
      style={{
        border: isHighRisk
          ? '1.5px solid var(--fs-danger-border, rgba(224, 108, 117, 0.45))'
          : '1px solid var(--fs-border, #1B382E)',
      }}
    >
      {/* 1. Header */}
      <div className="flex-between" style={{ marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--fs-radius-sm, 8px)',
              backgroundColor: isHighRisk
                ? 'var(--fs-danger-surface, rgba(224, 108, 117, 0.15))'
                : 'var(--fs-accent-surface, rgba(141, 219, 146, 0.12))',
              color: isHighRisk ? 'var(--fs-danger-bright, #F08D95)' : 'var(--fs-accent, #8DDB92)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {isHighRisk ? <ShieldAlert size={20} /> : <ShieldCheck size={20} />}
          </div>
          <div>
            <h3 className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', margin: 0 }}>
              Scam & Threat Shield
            </h3>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              PROTECT Pillar
            </p>
          </div>
        </div>

        {result && (
          <StatusBadge
            variant={isHighRisk ? 'danger' : isMediumRisk ? 'warning' : 'success'}
            icon={isHighRisk ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
          >
            {isHighRisk ? 'HIGH RISK DETECTED' : isMediumRisk ? 'MODERATE CONCERN' : 'LOW RISK'}
          </StatusBadge>
        )}
      </div>

      {/* 2. Input Form View */}
      {!result ? (
        <div className="flex-col gap-4">
          <p className="text-secondary" style={{ margin: 0, fontSize: '0.95rem' }}>
            Paste any suspicious SMS, payment request, or email to assess phishing indicators and scam risk before taking action.
          </p>

          <div>
            <label htmlFor="scam-message-input" className="sr-only">
              Paste suspicious message text to evaluate
            </label>
            <textarea
              id="scam-message-input"
              rows={4}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              placeholder="Paste message text here (e.g. 'URGENT: Your account will be suspended today, click bit.ly link...')"
              style={{
                width: '100%',
                padding: '14px',
                borderRadius: 'var(--fs-radius-md, 14px)',
                backgroundColor: 'var(--fs-bg, #071510)',
                color: 'var(--fs-text, #F5F4EC)',
                border: '1px solid var(--fs-border, #1B382E)',
                fontSize: '0.95rem',
                resize: 'vertical',
              }}
            />
          </div>

          {errorMsg && (
            <p className="text-secondary" style={{ color: 'var(--fs-danger-bright, #F08D95)', margin: 0 }} role="alert">
              {errorMsg}
            </p>
          )}

          <div className="flex-row gap-3" style={{ flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn"
              onClick={() => handleCheck()}
              disabled={isChecking || !messageInput.trim()}
              style={{ minHeight: '46px' }}
              aria-label="Analyze message for security risk"
            >
              <Search size={16} aria-hidden="true" />
              <span>{isChecking ? 'Evaluating Safety Indicators...' : 'Check Message Safety'}</span>
            </button>

            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleSampleMessage}
              disabled={isChecking}
              style={{ minHeight: '46px', fontSize: '14px' }}
            >
              <Sparkles size={16} aria-hidden="true" />
              <span>Load Sample Phishing SMS</span>
            </button>
          </div>
        </div>
      ) : (
        /* 3. Assessment Results View */
        <div
          className="flex-col gap-4"
          role={isHighRisk ? 'alert' : 'status'}
          aria-live={isHighRisk ? 'assertive' : 'polite'}
        >
          {/* Explanation Text */}
          <div
            style={{
              padding: '1rem 1.25rem',
              borderRadius: 'var(--fs-radius-md, 14px)',
              backgroundColor: 'var(--fs-bg, #071510)',
              border: '1px solid var(--fs-border-subtle, #142E25)',
            }}
          >
            <p
              className="text-body"
              style={{
                margin: 0,
                fontSize: '1rem',
                lineHeight: 1.6,
                color: isHighRisk ? 'var(--fs-danger-bright, #F08D95)' : 'var(--fs-text, #F5F4EC)',
                fontWeight: 500,
              }}
            >
              {result.explanation || result.answer_text}
            </p>
          </div>

          {/* Indicators List */}
          {result.indicators && result.indicators.length > 0 && (
            <div>
              <p
                className="text-meta"
                style={{
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontWeight: 600,
                  color: 'var(--fs-text-muted, #71817A)',
                  marginBottom: '0.5rem',
                }}
              >
                Detected Security Indicators
              </p>
              <div className="flex-col gap-2">
                {result.indicators.map((ind, i) => (
                  <div
                    key={i}
                    style={{
                      display: 'flex',
                      alignItems: 'flex-start',
                      gap: '0.6rem',
                      padding: '8px 12px',
                      borderRadius: 'var(--fs-radius-sm, 8px)',
                      backgroundColor: 'var(--fs-surface-elevated, #132D24)',
                      fontSize: '0.9rem',
                    }}
                  >
                    <AlertTriangle
                      size={16}
                      color="var(--fs-warning, #E6B85C)"
                      style={{ marginTop: '2px', flexShrink: 0 }}
                      aria-hidden="true"
                    />
                    <div>
                      <strong style={{ textTransform: 'capitalize', color: 'var(--fs-text, #F5F4EC)' }}>
                        {ind.type?.replace(/_/g, ' ')}:
                      </strong>{' '}
                      <span className="text-secondary">{ind.evidence}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Recommended Actions */}
          {result.recommended_actions && result.recommended_actions.length > 0 && (
            <div>
              <p
                className="text-meta"
                style={{
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontWeight: 600,
                  color: 'var(--fs-text-muted, #71817A)',
                  marginBottom: '0.5rem',
                }}
              >
                Recommended Protective Actions
              </p>
              <ul style={{ margin: 0, paddingLeft: '1.25rem' }} className="flex-col gap-2">
                {result.recommended_actions.map((act, i) => (
                  <li key={i} className="text-secondary" style={{ fontSize: '0.925rem' }}>
                    {act}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Reset Action */}
          <div style={{ marginTop: '0.5rem' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={reset}
              style={{ minHeight: '42px', fontSize: '14px' }}
            >
              <RotateCcw size={16} aria-hidden="true" />
              <span>Check Another Message</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
