import React, { useState } from 'react';
import { ShieldAlert, ShieldCheck, AlertTriangle, CheckCircle2, RotateCcw, Search, Sparkles } from 'lucide-react';
import { api } from '../services/api';
import StatusBadge from './StatusBadge';

/**
 * ScamChecker Component
 * FinSight's built-in financial security copilot (PROTECT Pillar).
 * Evaluates messages, payment requests, and SMS for fraud heuristics.
 */
export default function ScamChecker({ onAnnounce }) {
  const [messageInput, setMessageInput] = useState('');
  const [result, setResult] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleCheck = async (textToCheck = null) => {
    const text = textToCheck || messageInput;
    if (!text || !text.trim()) {
      const emptyMsg = 'Please enter or paste the message you want to evaluate.';
      setErrorMsg(emptyMsg);
      if (onAnnounce) onAnnounce(emptyMsg);
      return;
    }

    setIsChecking(true);
    setErrorMsg('');
    if (onAnnounce) onAnnounce('Analyzing message for security and fraud indicators...');

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
    <div className={`security-panel ${isHighRisk ? 'high-risk' : ''}`} aria-labelledby="security-check-heading">
      {/* 1. Header */}
      <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--fs-radius-md)',
              backgroundColor: isHighRisk
                ? 'var(--fs-danger-surface)'
                : 'var(--fs-accent-surface)',
              color: isHighRisk ? 'var(--fs-danger-bright)' : 'var(--fs-accent)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              border: isHighRisk ? '1px solid var(--fs-danger-border)' : '1px solid rgba(141, 219, 146, 0.25)',
            }}
          >
            {isHighRisk ? <ShieldAlert size={22} /> : <ShieldCheck size={22} />}
          </div>
          <div>
            <h2 id="security-check-heading" className="text-card-heading" style={{ color: 'var(--fs-text)', margin: 0 }}>
              Security Check
            </h2>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              PROTECT Pillar · Scam & Phishing Detection
            </p>
          </div>
        </div>

        {result && (
          <StatusBadge
            variant={isHighRisk ? 'danger' : isMediumRisk ? 'warning' : 'success'}
            icon={isHighRisk ? <AlertTriangle size={14} /> : <CheckCircle2 size={14} />}
          >
            {isHighRisk ? 'HIGH RISK DETECTED' : isMediumRisk ? 'MODERATE CONCERN' : 'LOW RISK VERIFIED'}
          </StatusBadge>
        )}
      </div>

      {/* 2. Message Input Form */}
      {!result ? (
        <div className="flex-col gap-4">
          <p className="text-secondary" style={{ margin: 0, fontSize: '0.95rem', lineHeight: 1.55 }}>
            Paste any suspicious payment notification, KYC request, or SMS to assess phishing signatures and fraudulent patterns before responding.
          </p>

          <div>
            <label htmlFor="security-message-input" className="sr-only">
              Suspicious message text to inspect
            </label>
            <textarea
              id="security-message-input"
              rows={4}
              value={messageInput}
              onChange={(e) => setMessageInput(e.target.value)}
              placeholder="Paste suspicious message here (e.g. 'URGENT: Your account will be frozen within 24 hours, click bit.ly link...')"
              style={{
                width: '100%',
                padding: '14px 16px',
                borderRadius: 'var(--fs-radius-md)',
                backgroundColor: 'var(--fs-bg)',
                color: 'var(--fs-text)',
                border: '1px solid var(--fs-border)',
                fontSize: '0.95rem',
                lineHeight: 1.5,
              }}
            />
          </div>

          {errorMsg && (
            <p className="text-secondary" style={{ color: 'var(--fs-danger-bright)', margin: 0 }} role="alert">
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
              style={{ minHeight: '46px', fontSize: '13px' }}
            >
              <Sparkles size={15} aria-hidden="true" />
              <span>Load Sample Phishing SMS</span>
            </button>
          </div>
        </div>
      ) : (
        /* 3. Security Analysis Result Surface */
        <div
          className="flex-col gap-4"
          role={isHighRisk ? 'alert' : 'status'}
          aria-live={isHighRisk ? 'assertive' : 'polite'}
        >
          {/* Assessment Summary Box */}
          <div
            style={{
              padding: '1.25rem 1.5rem',
              borderRadius: 'var(--fs-radius-md)',
              backgroundColor: 'var(--fs-bg)',
              border: isHighRisk ? '1px solid var(--fs-danger-border)' : '1px solid var(--fs-border)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, color: isHighRisk ? 'var(--fs-danger-bright)' : 'var(--fs-accent)' }}>
                Risk Assessment Summary
              </span>
            </div>
            <p
              className="text-body"
              style={{
                margin: 0,
                fontSize: '1rem',
                lineHeight: 1.6,
                color: isHighRisk ? 'var(--fs-danger-bright)' : 'var(--fs-text)',
                fontWeight: 500,
              }}
            >
              {result.explanation || result.answer_text}
            </p>
          </div>

          {/* Detected Indicator Badges */}
          {result.indicators && result.indicators.length > 0 && (
            <div>
              <p
                className="text-meta"
                style={{
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontWeight: 600,
                  color: 'var(--fs-text-muted)',
                  marginBottom: '0.6rem',
                }}
              >
                Why FinSight Flagged This
              </p>
              <div className="flex-col gap-2">
                {result.indicators.map((ind, i) => (
                  <div key={i} className="indicator-chip">
                    <AlertTriangle
                      size={16}
                      color="var(--fs-warning)"
                      style={{ marginTop: '2px', flexShrink: 0 }}
                      aria-hidden="true"
                    />
                    <div>
                      <strong style={{ textTransform: 'capitalize', color: 'var(--fs-text)' }}>
                        {ind.type?.replace(/_/g, ' ')}:
                      </strong>{' '}
                      <span className="text-secondary">{ind.evidence}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Protective Recommendations */}
          {result.recommended_actions && result.recommended_actions.length > 0 && (
            <div>
              <p
                className="text-meta"
                style={{
                  textTransform: 'uppercase',
                  letterSpacing: '1px',
                  fontWeight: 600,
                  color: 'var(--fs-text-muted)',
                  marginBottom: '0.6rem',
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
              style={{ minHeight: '40px', fontSize: '13px' }}
            >
              <RotateCcw size={15} aria-hidden="true" />
              <span>Check Another Message</span>
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
