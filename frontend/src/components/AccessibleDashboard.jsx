import React, { useState } from 'react';
import { Key, ShieldCheck, LogOut, Sparkles, User } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import StatusBadge from './StatusBadge';

/**
 * AccessibleDashboard Component
 * Top-level application shell with accessibility skip-link,
 * sticky premium FinSight navbar, passkey management, and ARIA live announcements.
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
    <div className="app-shell">
      {/* 1. Accessibility Skip Link */}
      <a href="#main-content" className="skip-link">
        Skip to main financial content
      </a>

      {/* 2. Premium Sticky App Header */}
      <header className="app-header" role="banner">
        {/* Left: Brand Identity */}
        <div className="header-brand">
          <div className="brand-emblem" aria-hidden="true">
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#071510' }} />
          </div>
          <div>
            <span className="brand-name">FIN•SIGHT</span>
            <span className="text-meta" style={{ display: 'block', fontSize: '10px', textTransform: 'uppercase', letterSpacing: '1px', color: 'var(--fs-accent)' }}>
              Deterministic Copilot
            </span>
          </div>
        </div>

        {/* Right: User Status & Security Controls */}
        <div className="header-user-status">
          {user && (
            <div className="user-badge" aria-label={`Logged in as ${user.full_name}`}>
              <User size={14} color="var(--fs-accent)" aria-hidden="true" />
              <span>{user.full_name}</span>
            </div>
          )}

          {!user?.has_passkey ? (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={handleAddPasskey}
              disabled={isRegisteringPasskey}
              style={{ minHeight: '38px', padding: '6px 14px', fontSize: '13px' }}
              aria-label="Register device biometric passkey"
            >
              <Key size={15} color="var(--fs-accent)" aria-hidden="true" />
              <span>{isRegisteringPasskey ? 'Registering...' : 'Add Passkey'}</span>
            </button>
          ) : (
            <StatusBadge variant="success" icon={<ShieldCheck size={14} />}>
              Passkey Active
            </StatusBadge>
          )}

          <button
            type="button"
            className="btn btn-secondary"
            onClick={logout}
            aria-label="Sign out of FinSight account"
            style={{ minHeight: '38px', padding: '6px 14px', fontSize: '13px' }}
          >
            <LogOut size={15} aria-hidden="true" />
            <span>Sign Out</span>
          </button>
        </div>
      </header>

      {/* 3. Passkey Status Notice Banner */}
      {passkeyNotice && (
        <div
          className="container"
          style={{ padding: '1rem 1.25rem 0' }}
          role="status"
          aria-live="polite"
        >
          <div
            className="card-elevated"
            style={{
              padding: '0.85rem 1.25rem',
              backgroundColor: 'var(--fs-accent-surface)',
              borderColor: 'var(--fs-accent)',
              display: 'flex',
              alignItems: 'center',
              gap: '0.75rem',
            }}
          >
            <Sparkles size={18} color="var(--fs-accent)" aria-hidden="true" />
            <p className="text-body" style={{ margin: 0, fontSize: '0.925rem' }}>
              {passkeyNotice}
            </p>
          </div>
        </div>
      )}

      {/* 4. Main Application Viewport Landmark */}
      <main id="main-content" className="main-content-container" tabIndex={-1}>
        {children}
      </main>
    </div>
  );
}
