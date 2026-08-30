import React, { useState } from 'react';

export default function ScamChecker({ onAnnounce }) {
  const [result, setResult] = useState(null); // null | 'SAFE' | 'WARNING'
  const [isChecking, setIsChecking] = useState(false);

  const checkScam = () => {
    setIsChecking(true);
    onAnnounce("Checking message for potential threats...");
    
    setTimeout(() => {
      setIsChecking(false);
      setResult('WARNING');
      onAnnounce("Potential scam detected. FinSight found 3 warning signs: Urgency, Sensitive information request, and Suspicious link. Recommendation: Do not click the link or share sensitive information.");
    }, 2000);
  };

  const reset = () => {
    setResult(null);
  };

  return (
    <div className="card">
      {!result ? (
        <>
          <h3 className="text-card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            🛡 Is this message suspicious?
          </h3>
          <p className="text-secondary" style={{ marginTop: '0.5rem', marginBottom: '1.5rem' }}>
            Paste, upload or read the message to FinSight.
          </p>
          
          <div className="flex-col gap-4">
            <button className="btn btn-secondary" onClick={checkScam} disabled={isChecking}>
              {isChecking ? 'Checking...' : '🎙 Speak message'}
            </button>
            <button className="btn btn-secondary" onClick={checkScam} disabled={isChecking}>
              Paste message
            </button>
            <button className="btn btn-secondary" onClick={checkScam} disabled={isChecking}>
              Upload screenshot
            </button>
          </div>
        </>
      ) : result === 'WARNING' ? (
        <div className="animate-fade-in">
          <h3 className="text-card-heading color-warning" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
            ⚠️ POTENTIAL SCAM
          </h3>
          <p className="text-body" style={{ marginTop: '0.5rem', marginBottom: '1.5rem' }}>
            FinSight found 3 warning signs.
          </p>
          
          <ol style={{ paddingLeft: '1.5rem', margin: '0 0 1.5rem 0', display: 'flex', flexDirection: 'column', gap: '1rem' }} className="text-body">
            <li>
              <strong>Urgency</strong><br/>
              <span className="text-secondary">The message pressures you to act quickly.</span>
            </li>
            <li>
              <strong>Sensitive information</strong><br/>
              <span className="text-secondary">It asks for account information.</span>
            </li>
            <li>
              <strong>Suspicious link</strong><br/>
              <span className="text-secondary">It asks you to use an unfamiliar link.</span>
            </li>
          </ol>
          
          <div style={{ padding: '1rem', backgroundColor: 'rgba(230, 184, 92, 0.1)', borderRadius: '12px', border: '1px solid rgba(230, 184, 92, 0.2)', marginBottom: '1.5rem' }}>
            <h4 className="text-secondary" style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem', fontSize: '12px' }}>Recommendation</h4>
            <p className="text-body color-warning">Do not click the link or share sensitive information until you verify the sender.</p>
          </div>

          <div className="flex-col gap-4">
            <button className="btn btn-secondary" onClick={() => onAnnounce("Potential scam detected. FinSight found 3 warning signs: Urgency, Sensitive information request, and Suspicious link. Recommendation: Do not click the link or share sensitive information.")}>
              Hear explanation again
            </button>
            <button className="btn btn-secondary" onClick={reset}>
              Check another message
            </button>
          </div>
        </div>
      ) : null}
    </div>
  );
}
