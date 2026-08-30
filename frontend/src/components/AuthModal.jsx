import React from 'react';

export default function AuthModal({ isOpen, onAuthenticate, onCancel }) {
  if (!isOpen) return null;

  return (
    <div 
      className="modal-backdrop" 
      style={{
        position: 'fixed', top: 0, left: 0, width: '100vw', height: '100vh',
        backgroundColor: 'rgba(0,0,0,0.8)', display: 'flex', 
        justifyContent: 'center', alignItems: 'center', zIndex: 9999
      }}
      role="dialog"
      aria-modal="true"
      aria-labelledby="auth-title"
      aria-describedby="auth-desc"
    >
      <div 
        className="card" 
        style={{ width: '90%', maxWidth: '400px', textAlign: 'center', border: '2px solid var(--color-primary)' }}
      >
        <h2 id="auth-title" className="text-page-heading" style={{ marginBottom: '1rem', color: 'var(--color-primary)' }}>
          Confirm Payment
        </h2>
        <p id="auth-desc" className="text-body" style={{ marginBottom: '2rem' }}>
          Please authenticate with Face ID or Touch ID to safely authorize this transaction.
        </p>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
          <button 
            className="btn" 
            style={{ 
              padding: '16px', fontSize: '1.2rem', backgroundColor: 'var(--color-primary)', 
              color: 'var(--color-bg)', border: 'none', borderRadius: '8px', cursor: 'pointer'
            }}
            onClick={onAuthenticate}
          >
            ✅ Authenticate (Simulate Success)
          </button>
          
          <button 
            className="btn" 
            style={{ 
              padding: '12px', fontSize: '1rem', backgroundColor: 'transparent', 
              color: 'var(--color-text)', border: '2px solid var(--color-text-muted)', borderRadius: '8px', cursor: 'pointer'
            }}
            onClick={onCancel}
          >
            ❌ Cancel
          </button>
        </div>
      </div>
    </div>
  );
}
