import React, { useState } from 'react';
import { Key, ShieldCheck, LogOut, Sparkles } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import StatusBadge from './StatusBadge';

/**
 * AccessibleDashboard Component
 * Top-level application shell with accessibility skip-link,
 * FinSight brand header, passkey management, and ARIA live regions.
 */
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
      const successMsg = 'Device passkey registered successfully. You can now use biometric authentication to sign in.';
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
    <div className="container" style={{ padding: '1.5rem 1.25rem 3rem' }}>
      {/* 1. Accessibility Skip Link */}
      <a href="#main-content" className="skip-link">
        Skip to main content
      </a>

      {/* 2. Application Header */}
      <header
        role="banner"
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '1rem',
          marginBottom: '2rem',
          borderBottom: '1px solid var(--fs-border, #1B382E)',
          paddingBottom: '1.25rem',
        }}
      >
        {/* Brand Identity */}
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <span
              style={{
                width: '10px',
                height: '10px',
                borderRadius: '50%',
                backgroundColor: 'var(--fs-accent, #8DDB92)',
                boxShadow: '0 0 10px var(--fs-accent, #8DDB92)',
                display: 'inline-block',
              }}
              aria-hidden="true"
            />
            <h1
              className="text-section-heading"
              style={{
                letterSpacing: '1.5px',
                fontWeight: 700,
                color: 'var(--fs-text, #F5F4EC)',
                margin: 0,
                fontSize: '1.25rem',
                textTransform: 'uppercase',
              }}
            >
              FIN•SIGHT
            </h1>
          </div>
          {user && (
            <p className="text-secondary" style={{ fontSize: '0.875rem', marginTop: '0.35rem' }}>
              Financial Copilot · <strong>{user.full_name}</strong>
            </p>
          )}
        </div>

        {/* Security & Session Controls */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
          {!user?.has_passkey && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddPasskey}
              disabled={isRegisteringPasskey}
              style={{ minHeight: '40px', padding: '6px 14px', fontSize: '0.85rem' }}
              aria-label="Add Device Passkey for biometric sign in"
            >
              <Key size={16} aria-hidden="true" />
              <span>{isRegisteringPasskey ? 'Registering...' : 'Add Passkey'}</span>
            </button>
          )}

          {user?.has_passkey && (
            <StatusBadge variant="success" icon={<ShieldCheck size={15} />}>
              Passkey Active
            </StatusBadge>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={logout}
            aria-label="Sign Out of FinSight"
            style={{ minHeight: '40px', padding: '6px 14px', fontSize: '0.85rem' }}
          >
            <LogOut size={16} aria-hidden="true" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* Passkey Live Announcement Card */}
      {passkeyNotice && (
        <div
          className="card card-elevated"
          style={{
            marginBottom: '1.5rem',
            padding: '1rem 1.25rem',
            backgroundColor: 'var(--fs-accent-surface, rgba(141, 219, 146, 0.10))',
            borderColor: 'var(--fs-accent, #8DDB92)',
          }}
          role="status"
          aria-live="polite"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
            <Sparkles size={18} color="var(--fs-accent, #8DDB92)" aria-hidden="true" />
            <p className="text-body" style={{ margin: 0, fontSize: '0.925rem' }}>
              {passkeyNotice}
            </p>
          </div>
        </div>
      )}

      {/* Main Content Landmark */}
      <main id="main-content" className="flex-col gap-8" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
