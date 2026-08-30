import React, { useState } from 'react';
import { api } from '../services/api';

export default function ScamChecker({ onAnnounce }) {
  const [messageInput, setMessageInput] = useState('');
  const [result, setResult] = useState(null);
  const [isChecking, setIsChecking] = useState(false);
  const [errorMsg, setErrorMsg] = useState('');

  const handleCheck = async (textToCheck = null) => {
    const text = textToCheck || messageInput;
    if (!text || !text.trim()) {
      setErrorMsg('Please paste or enter the message you want to check.');
      if (onAnnounce) onAnnounce('Please paste or enter the message you want to check.');
      return;
    }

    setIsChecking(true);
    setErrorMsg('');
    if (onAnnounce) onAnnounce('Analyzing message for potential security risks...');

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
    const sample = 'URGENT: Your HDFC Bank account will be blocked within 24 hours due to pending KYC. Click http://bit.ly/hdfc-kyc-verify to update now.';
    setMessageInput(sample);
    handleCheck(sample);
  };

  return (
    <div className="card">
      {!result ? (
        <>
          <h3 className="text-card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🛡 Is this message suspicious?
          </h3>
          <p className="text-secondary" style={{ marginTop: '0.5rem', marginBottom: '1rem' }}>
            Paste a suspicious SMS, email, or chat message to assess scam risk.
          </p>

          <div className="flex-col gap-4">
            <div>
              <label htmlFor="scam-message-text" className="sr-only">
                Suspicious message text
              </label>
              <textarea
                id="scam-message-text"
                rows={4}
                value={messageInput}
                onChange={(e) => setMessageInput(e.target.value)}
                placeholder="Paste message here (e.g., 'URGENT: Your account is suspended, click link to verify...')"
                className="input"
                style={{
                  width: '100%',
                  padding: '12px',
                  borderRadius: '8px',
                  backgroundColor: 'var(--color-bg)',
                  color: 'var(--color-text)',
                  border: '1px solid var(--color-border)',
                  resize: 'vertical',
                  fontSize: '0.95rem',
                }}
              />
            </div>

            {errorMsg && (
              <p className="text-body" style={{ color: 'var(--color-error)' }} role="alert">
                {errorMsg}
              </p>
            )}

            <div className="flex-col gap-2">
              <button
                type="button"
                className="btn"
                onClick={() => handleCheck()}
                disabled={isChecking || !messageInput.trim()}
              >
                {isChecking ? 'Analyzing Message...' : '🔍 Check Message Safety'}
              </button>

              <button
                type="button"
                className="btn btn-secondary"
                onClick={handleSampleMessage}
                disabled={isChecking}
                style={{ fontSize: '0.85rem' }}
              >
                Try Sample Suspicious SMS
              </button>
            </div>
          </div>
        </>
      ) : (
        <div className="animate-fade-in">
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: '1rem',
            }}
          >
            <h3
              className={`text-card-heading ${result.looks_suspicious ? 'color-warning' : 'color-primary'}`}
              style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}
            >
              {result.looks_suspicious ? '⚠️ POTENTIAL SCAM / RISK' : '✅ LOW SCAM RISK'}
            </h3>
            <span
              style={{
                padding: '4px 10px',
                borderRadius: '12px',
                fontSize: '0.8rem',
                fontWeight: 600,
                textTransform: 'uppercase',
                backgroundColor: result.looks_suspicious ? 'rgba(230, 184, 92, 0.2)' : 'rgba(16, 185, 129, 0.2)',
                color: result.looks_suspicious ? 'var(--color-warning)' : 'var(--color-success)',
              }}
            >
              Risk: {result.risk_level}
            </span>
          </div>

          <p className="text-body" style={{ marginBottom: '1.25rem' }}>
            {result.explanation}
          </p>

          {/* INDICATORS RETURNED BY BACKEND */}
          {result.indicators && result.indicators.length > 0 && (
            <div style={{ marginBottom: '1.5rem' }}>
              <h4
                className="text-secondary"
                style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem', fontSize: '12px' }}
              >
                Warning Signs Detected ({result.indicators.length})
              </h4>
              <ol
                style={{
                  paddingLeft: '1.25rem',
                  margin: 0,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '0.75rem',
                }}
                className="text-body"
              >
                {result.indicators.map((ind, idx) => (
                  <li key={idx}>
                    <strong>{String(ind.type || 'Indicator').replace(/_/g, ' ').toUpperCase()}</strong>
                    <br />
                    <span className="text-secondary">"{ind.evidence}"</span>
                  </li>
                ))}
              </ol>
            </div>
          )}

          {/* ACTIONS RETURNED BY BACKEND */}
          {result.recommended_actions && result.recommended_actions.length > 0 && (
            <div
              style={{
                padding: '1rem',
                backgroundColor: 'rgba(230, 184, 92, 0.1)',
                borderRadius: '8px',
                border: '1px solid rgba(230, 184, 92, 0.2)',
                marginBottom: '1.5rem',
              }}
            >
              <h4
                className="text-secondary"
                style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem', fontSize: '12px' }}
              >
                Recommended Actions
              </h4>
              <ul style={{ paddingLeft: '1.25rem', margin: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {result.recommended_actions.map((action, idx) => (
                  <li key={idx} className="text-body" style={{ fontSize: '0.9rem' }}>
                    {action}
                  </li>
                ))}
              </ul>
            </div>
          )}

          <p className="text-secondary" style={{ fontSize: '0.8rem', fontStyle: 'italic', marginBottom: '1.5rem' }}>
            {result.limitations}
          </p>

          <div className="flex-col gap-2">
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => onAnnounce && onAnnounce(result.answer_text)}
            >
              🔊 Hear Explanation Again
            </button>
            <button type="button" className="btn btn-secondary" onClick={reset}>
              Check Another Message
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
