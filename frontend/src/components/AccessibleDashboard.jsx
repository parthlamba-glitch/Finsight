import React, { useState } from 'react';
import { useAuth } from '../hooks/useAuth';

export default function AccessibleDashboard({ children, onAnnounce }) {
  const { user, logout, registerPasskey } = useAuth();
  const [isRegisteringPasskey, setIsRegisteringPasskey] = useState(false);
  const [passkeyNotice, setPasskeyNotice] = useState('');

  const handleAddPasskey = async () => {
    setIsRegisteringPasskey(true);
    setPasskeyNotice('Registering device passkey...');
    if (onAnnounce) onAnnounce('Please verify on your device authenticator to add a passkey.');

    try {
      await registerPasskey('My FinSight Device Passkey');
      const successMsg = 'Device passkey registered successfully! You can now use it to sign in.';
      setPasskeyNotice(successMsg);
      if (onAnnounce) onAnnounce(successMsg);
    } catch (err) {
      const errMsg = err.message || 'Failed to register passkey.';
      setPasskeyNotice(errMsg);
      if (onAnnounce) onAnnounce(errMsg);
    } finally {
      setIsRegisteringPasskey(false);
    }
  };

  return (
    <div className="container" style={{ padding: '2rem 1rem' }}>
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2rem',
          borderBottom: '1px solid var(--color-border)',
          paddingBottom: '1rem',
        }}
      >
        <div>
          <h1
            className="text-section-heading color-primary"
            style={{ letterSpacing: '2px', display: 'flex', alignItems: 'center', gap: '0.5rem', margin: 0 }}
          >
            ◉ FIN•SIGHT
          </h1>
          {user && (
            <p className="text-secondary" style={{ fontSize: '0.9rem', marginTop: '0.25rem' }}>
              Logged in as <strong>{user.full_name}</strong>
            </p>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {!user?.has_passkey && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddPasskey}
              disabled={isRegisteringPasskey}
              style={{ minHeight: '38px', padding: '6px 14px', fontSize: '0.85rem' }}
              aria-label="Add Device Passkey"
            >
              {isRegisteringPasskey ? 'Adding...' : '🔑 Add Passkey'}
            </button>
          )}

          {user?.has_passkey && (
            <span
              style={{
                fontSize: '0.8rem',
                padding: '4px 8px',
                borderRadius: '6px',
                backgroundColor: 'rgba(16, 185, 129, 0.15)',
                color: 'var(--color-success)',
                fontWeight: 600,
              }}
              title="Device Passkey Registered"
            >
              🔑 Passkey Active
            </span>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={logout}
            aria-label="Sign Out"
            style={{ minHeight: '38px', padding: '6px 14px', fontSize: '0.85rem' }}
          >
            Sign Out
          </button>
        </div>
      </header>

      {passkeyNotice && (
        <div
          className="card"
          style={{
            marginBottom: '1.5rem',
            padding: '0.75rem 1rem',
            backgroundColor: 'rgba(230, 184, 92, 0.1)',
            borderColor: 'var(--color-primary)',
          }}
          role="status"
          aria-live="polite"
        >
          <p className="text-body" style={{ margin: 0, fontSize: '0.9rem' }}>
            {passkeyNotice}
          </p>
        </div>
      )}

      <main className="flex-col gap-8">{children}</main>
    </div>
  );
}
