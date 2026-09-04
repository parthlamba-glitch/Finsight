import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { motion, AnimatePresence } from 'framer-motion';
import { Key, ShieldCheck, UserCheck, AlertCircle, ArrowRight, Mic, CheckCircle2 } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useSpeech } from '../hooks/useSpeech';
import VoiceOrb from '../components/VoiceOrb';
import StatusBadge from '../components/StatusBadge';

/**
 * Login Component
 * Premium split-screen fintech authentication experience with FIDO2 passkeys,
 * password fallback, WCAG AAA accessibility preferences, and voice navigation.
 */
export default function Login() {
  const navigate = useNavigate();
  const { login, signup, loginWithPasskey, authError, clearError } = useAuth();

  const [mode, setMode] = useState('login'); // 'login' | 'signup' | 'passkey'
  const [isStarted, setIsStarted] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Form State
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  // Accessibility Preferences
  const [highContrast, setHighContrast] = useState(false);
  const [screenReaderOptimized, setScreenReaderOptimized] = useState(true);

  const formRef = useRef(null);

  // Voice command callback
  const handleVoiceCommand = useCallback(
    async (transcript) => {
      const lower = transcript.toLowerCase();

      if (lower.includes('passkey') || lower.includes('biometric') || lower.includes('device')) {
        setMode('passkey');
        handlePasskeyLogin();
      } else if (lower.includes('create account') || lower.includes('sign up') || lower.includes('register')) {
        setMode('signup');
        speak("Switched to Create Account. Please enter your name, email, and password.", () => {
          if (formRef.current) formRef.current.focus();
        });
      } else if (lower.includes('sign in') || lower.includes('log in') || lower.includes('password')) {
        setMode('login');
        speak("Switched to Sign In. Please enter your email and password.", () => {
          if (formRef.current) formRef.current.focus();
        });
      } else {
        speak("You can say 'Sign in', 'Create account', or 'Use passkey'.", () => {
          startListening();
        });
      }
    },
    // eslint-disable-next-line react-hooks/exhaustive-deps
    []
  );

  const { speak, startListening, isListening, isSpeaking, isProcessing } =
    useSpeech((transcript) => {
      handleVoiceCommand(transcript);
    });

  const handleStart = () => {
    if (!isStarted) {
      setIsStarted(true);
      speak(
        "Welcome to FinSight. How would you like to sign in? You can say 'Sign in', 'Create account', or 'Use passkey'.",
        () => {
          startListening();
        }
      );
    }
  };

  const handlePasswordLogin = async (e) => {
    if (e) e.preventDefault();
    if (!email || !password) {
      const msg = 'Please enter both email and password.';
      setStatusMessage(msg);
      speak(msg);
      return;
    }

    setIsSubmitting(true);
    setStatusMessage('Signing in to your account...');
    clearError();

    try {
      await login(email, password);
      speak('Signed in successfully. Welcome to your financial dashboard.', () => {
        navigate('/dashboard');
      });
    } catch (err) {
      const msg = err.message || 'Login failed. Please verify your credentials.';
      setStatusMessage(msg);
      speak(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSignupSubmit = async (e) => {
    if (e) e.preventDefault();
    if (!name || !email || !password) {
      const msg = 'Please fill in all required fields.';
      setStatusMessage(msg);
      speak(msg);
      return;
    }

    if (password.length < 8) {
      const lenMsg = 'Password must be at least 8 characters long.';
      setStatusMessage(lenMsg);
      speak(lenMsg);
      return;
    }

    setIsSubmitting(true);
    setStatusMessage('Creating your account...');
    clearError();

    try {
      await signup({
        name,
        email,
        password,
        accessibility_prefs: {
          high_contrast: highContrast,
          screen_reader_optimized: screenReaderOptimized,
          voice_first: true,
          tts_speed: 1.0,
          simplified_view: false,
          announce_all_changes: true,
        },
      });

      speak('Account created successfully. Welcome to FinSight.', () => {
        navigate('/dashboard');
      });
    } catch (err) {
      const msg = err.message || 'Registration failed. Please try again.';
      setStatusMessage(msg);
      speak(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handlePasskeyLogin = async () => {
    setIsSubmitting(true);
    setStatusMessage('Initiating device biometric passkey authentication...');
    clearError();

    try {
      await loginWithPasskey(email || null);
      speak('Passkey verified successfully. Welcome back to FinSight.', () => {
        navigate('/dashboard');
      });
    } catch (err) {
      const msg = err.message || 'Passkey authentication failed.';
      setStatusMessage(msg);
      speak(msg);
    } finally {
      setIsSubmitting(false);
    }
  };

  const getStatusText = () => {
    if (statusMessage) return statusMessage;
    if (authError) return authError;
    if (isListening) return 'Listening... Speak your command';
    if (isProcessing) return 'Understanding speech...';
    if (isSpeaking) return 'FinSight is speaking...';
    if (!isStarted) return 'Click anywhere or press Space to enable voice navigation';
    return '"How would you like to sign in today?"';
  };

  return (
    <div
      className="login-split-page"
      onClick={!isStarted ? handleStart : undefined}
      onKeyDown={
        !isStarted
          ? (e) => {
              if (e.key === 'Enter' || e.key === ' ') handleStart();
            }
          : undefined
      }
      tabIndex={!isStarted ? 0 : undefined}
      role={!isStarted ? 'button' : undefined}
      aria-label={!isStarted ? 'Click anywhere or press Enter to activate FinSight voice navigation.' : undefined}
    >
      {/* 1. LEFT BRAND & VALUE PANEL (DESKTOP) */}
      <div className="login-brand-panel">
        <div>
          {/* Brand Header */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', marginBottom: '3.5rem' }}>
            <div className="brand-emblem" aria-hidden="true">
              <span style={{ width: '8px', height: '8px', borderRadius: '50%', backgroundColor: '#071510' }} />
            </div>
            <span className="brand-name">FIN•SIGHT</span>
            <StatusBadge variant="neutral" icon={<ShieldCheck size={13} />}>
              WCAG 2.2 AAA
            </StatusBadge>
          </div>

          {/* Value Prop Headline */}
          <div style={{ maxWidth: '540px' }}>
            <div style={{ display: 'inline-flex', gap: '0.5rem', marginBottom: '1.25rem' }}>
              <StatusBadge variant="success" icon={<Mic size={12} />}>
                Voice-First Financial Copilot
              </StatusBadge>
            </div>

            <h1
              className="text-hero"
              style={{
                fontSize: 'clamp(2.5rem, 4.5vw, 3.75rem)',
                lineHeight: 1.06,
                letterSpacing: '-0.03em',
                marginBottom: '1.5rem',
                color: 'var(--fs-text)',
              }}
            >
              Your money,
              <br />
              <span style={{ color: 'var(--fs-accent)' }}>understood.</span>
            </h1>

            <p
              className="text-body"
              style={{
                fontSize: '1.15rem',
                lineHeight: 1.6,
                color: 'var(--fs-text-secondary)',
                marginBottom: '2.5rem',
              }}
            >
              A financial copilot designed around independence. Speak to your balances, verify suspicious transaction links, and authorize decisions with deterministic certainty.
            </p>

            {/* Core Feature Pillars */}
            <div className="flex-col gap-3" style={{ marginBottom: '2.5rem' }}>
              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
                <div style={{ color: 'var(--fs-accent)', marginTop: '2px' }}>
                  <CheckCircle2 size={18} />
                </div>
                <div>
                  <strong style={{ color: 'var(--fs-text)', fontSize: '0.95rem' }}>Voice-First Autonomy</strong>
                  <p className="text-secondary" style={{ fontSize: '0.875rem', margin: '2px 0 0' }}>
                    Ask about spending, surplus, and goals in natural language without visual charts.
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
                <div style={{ color: 'var(--fs-accent)', marginTop: '2px' }}>
                  <CheckCircle2 size={18} />
                </div>
                <div>
                  <strong style={{ color: 'var(--fs-text)', fontSize: '0.95rem' }}>Deterministic Protection</strong>
                  <p className="text-secondary" style={{ fontSize: '0.875rem', margin: '2px 0 0' }}>
                    AI explains your ledger; authoritative mathematical engines calculate every rupee.
                  </p>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'flex-start', gap: '0.85rem' }}>
                <div style={{ color: 'var(--fs-accent)', marginTop: '2px' }}>
                  <CheckCircle2 size={18} />
                </div>
                <div>
                  <strong style={{ color: 'var(--fs-text)', fontSize: '0.95rem' }}>FIDO2 Cryptographic Passkeys</strong>
                  <p className="text-secondary" style={{ fontSize: '0.875rem', margin: '2px 0 0' }}>
                    Sign in with device biometrics. Raw biometric data never leaves your hardware.
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Voice Navigation Cue Box */}
        <div
          className="card-elevated"
          style={{
            maxWidth: '500px',
            backgroundColor: 'rgba(15, 37, 30, 0.75)',
            border: '1px solid var(--fs-border-hover)',
          }}
        >
          <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, color: 'var(--fs-accent)', marginBottom: '0.25rem' }}>
            Acoustic Navigation Ready
          </p>
          <p className="text-body" style={{ fontStyle: 'italic', margin: 0, fontSize: '0.95rem' }}>
            "You can say 'Sign in', 'Create account', or 'Use passkey'."
          </p>
        </div>
      </div>

      {/* 2. RIGHT AUTHENTICATION SURFACE */}
      <div className="login-form-panel">
        <div className="auth-surface-box">
          {/* Central Voice Orb */}
          <div style={{ marginBottom: '0.5rem' }}>
            <VoiceOrb
              isListening={isListening}
              isProcessing={isProcessing}
              isSpeaking={isSpeaking || !isStarted}
            />
          </div>

          {/* Heading & Live Status */}
          <div style={{ textAlign: 'center', marginBottom: '1.75rem' }}>
            <h2 className="text-card-heading" style={{ fontSize: '1.35rem', color: 'var(--fs-text)' }}>
              {mode === 'signup' ? 'Create FinSight Account' : mode === 'passkey' ? 'Device Passkey Sign In' : 'Welcome to FinSight'}
            </h2>
            <p
              className="text-secondary"
              style={{
                marginTop: '0.5rem',
                fontSize: '0.9rem',
                minHeight: '22px',
                color: authError ? 'var(--fs-danger-bright)' : 'var(--fs-text-secondary)',
              }}
              aria-live="polite"
            >
              {getStatusText()}
            </p>
          </div>

          {/* Segmented Mode Selector */}
          <div
            role="tablist"
            aria-label="Authentication Mode"
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(3, 1fr)',
              gap: '4px',
              backgroundColor: 'var(--fs-bg)',
              padding: '4px',
              borderRadius: 'var(--fs-radius-md)',
              marginBottom: '1.75rem',
              border: '1px solid var(--fs-border)',
            }}
          >
            <button
              type="button"
              role="tab"
              aria-selected={mode === 'login'}
              className="btn btn-secondary"
              style={{
                minHeight: '36px',
                padding: '6px',
                fontSize: '0.85rem',
                backgroundColor: mode === 'login' ? 'var(--fs-surface-elevated)' : 'transparent',
                color: mode === 'login' ? 'var(--fs-accent)' : 'var(--fs-text-secondary)',
                border: mode === 'login' ? '1px solid var(--fs-border-focus)' : 'none',
              }}
              onClick={() => {
                setMode('login');
                clearError();
                setStatusMessage('');
              }}
            >
              Sign In
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mode === 'signup'}
              className="btn btn-secondary"
              style={{
                minHeight: '36px',
                padding: '6px',
                fontSize: '0.85rem',
                backgroundColor: mode === 'signup' ? 'var(--fs-surface-elevated)' : 'transparent',
                color: mode === 'signup' ? 'var(--fs-accent)' : 'var(--fs-text-secondary)',
                border: mode === 'signup' ? '1px solid var(--fs-border-focus)' : 'none',
              }}
              onClick={() => {
                setMode('signup');
                clearError();
                setStatusMessage('');
              }}
            >
              Register
            </button>

            <button
              type="button"
              role="tab"
              aria-selected={mode === 'passkey'}
              className="btn btn-secondary"
              style={{
                minHeight: '36px',
                padding: '6px',
                fontSize: '0.85rem',
                backgroundColor: mode === 'passkey' ? 'var(--fs-surface-elevated)' : 'transparent',
                color: mode === 'passkey' ? 'var(--fs-accent)' : 'var(--fs-text-secondary)',
                border: mode === 'passkey' ? '1px solid var(--fs-border-focus)' : 'none',
              }}
              onClick={() => {
                setMode('passkey');
                clearError();
                setStatusMessage('');
              }}
            >
              Passkey
            </button>
          </div>

          {/* Error Notice */}
          {authError && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: '0.6rem',
                padding: '10px 14px',
                backgroundColor: 'var(--fs-danger-surface)',
                border: '1px solid var(--fs-danger-border)',
                borderRadius: 'var(--fs-radius-sm)',
                marginBottom: '1.25rem',
                color: 'var(--fs-danger-bright)',
                fontSize: '0.875rem',
              }}
              role="alert"
            >
              <AlertCircle size={18} aria-hidden="true" />
              <span>{authError}</span>
            </div>
          )}

          {/* Form Content */}
          <AnimatePresence mode="wait">
            {mode === 'login' && (
              <motion.form
                key="login-form"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                onSubmit={handlePasswordLogin}
                className="flex-col gap-4"
                ref={formRef}
                tabIndex={-1}
              >
                <div>
                  <label htmlFor="login-email" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Email Address
                  </label>
                  <input
                    id="login-email"
                    type="email"
                    required
                    autoComplete="username"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="aarav.sharma@example.com"
                  />
                </div>

                <div>
                  <label htmlFor="login-password" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Password
                  </label>
                  <input
                    id="login-password"
                    type="password"
                    required
                    autoComplete="current-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>

                <button
                  type="submit"
                  className="btn"
                  disabled={isSubmitting}
                  style={{ width: '100%', marginTop: '0.5rem' }}
                >
                  <span>{isSubmitting ? 'Signing In...' : 'Sign In with Password'}</span>
                  <ArrowRight size={18} aria-hidden="true" />
                </button>

                <div style={{ position: 'relative', margin: '1rem 0', textAlign: 'center' }}>
                  <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '1px', backgroundColor: 'var(--fs-border)' }} />
                  <span style={{ position: 'relative', backgroundColor: 'var(--fs-surface-card)', padding: '0 12px', fontSize: '11px', color: 'var(--fs-text-muted)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                    Or use passwordless
                  </span>
                </div>

                {/* Prominent Passkey Action Button */}
                <button
                  type="button"
                  className="btn btn-secondary"
                  onClick={handlePasskeyLogin}
                  disabled={isSubmitting}
                  style={{
                    width: '100%',
                    borderColor: 'var(--fs-border-hover)',
                    backgroundColor: 'var(--fs-surface-elevated)',
                  }}
                >
                  <Key size={18} color="var(--fs-accent)" aria-hidden="true" />
                  <span>Sign In with Device Passkey</span>
                </button>
              </motion.form>
            )}

            {mode === 'signup' && (
              <motion.form
                key="signup-form"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                onSubmit={handleSignupSubmit}
                className="flex-col gap-4"
                ref={formRef}
                tabIndex={-1}
              >
                <div>
                  <label htmlFor="signup-name" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Full Name
                  </label>
                  <input
                    id="signup-name"
                    type="text"
                    required
                    autoComplete="name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    placeholder="Aarav Sharma"
                  />
                </div>

                <div>
                  <label htmlFor="signup-email" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Email Address
                  </label>
                  <input
                    id="signup-email"
                    type="email"
                    required
                    autoComplete="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="aarav.sharma@example.com"
                  />
                </div>

                <div>
                  <label htmlFor="signup-password" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Password (min 8 characters)
                  </label>
                  <input
                    id="signup-password"
                    type="password"
                    required
                    minLength={8}
                    autoComplete="new-password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="••••••••"
                  />
                </div>

                {/* Visible Accessibility Preferences */}
                <fieldset
                  style={{
                    border: '1px solid var(--fs-border)',
                    borderRadius: 'var(--fs-radius-md)',
                    padding: '12px 14px',
                    backgroundColor: 'var(--fs-bg)',
                    marginTop: '0.25rem',
                  }}
                >
                  <legend className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px', fontWeight: 600 }}>
                    Accessibility Preferences
                  </legend>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer', marginBottom: '8px' }}>
                    <input
                      type="checkbox"
                      checked={screenReaderOptimized}
                      onChange={(e) => setScreenReaderOptimized(e.target.checked)}
                    />
                    <span className="text-body" style={{ fontSize: '0.875rem' }}>
                      Screen reader optimization enabled
                    </span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={highContrast}
                      onChange={(e) => setHighContrast(e.target.checked)}
                    />
                    <span className="text-body" style={{ fontSize: '0.875rem' }}>
                      High contrast visual mode (WCAG AAA)
                    </span>
                  </label>
                </fieldset>

                <button
                  type="submit"
                  className="btn"
                  disabled={isSubmitting}
                  style={{ width: '100%', marginTop: '0.5rem' }}
                >
                  <UserCheck size={18} aria-hidden="true" />
                  <span>{isSubmitting ? 'Creating Account...' : 'Create Account'}</span>
                </button>
              </motion.form>
            )}

            {mode === 'passkey' && (
              <motion.div
                key="passkey-view"
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -8 }}
                transition={{ duration: 0.15 }}
                className="flex-col gap-4"
              >
                <div
                  style={{
                    backgroundColor: 'var(--fs-bg)',
                    border: '1px solid var(--fs-border)',
                    borderRadius: 'var(--fs-radius-md)',
                    padding: '1.25rem',
                    lineHeight: 1.5,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                    <Key size={18} color="var(--fs-accent)" aria-hidden="true" />
                    <span style={{ fontWeight: 600, color: 'var(--fs-text)', fontSize: '0.95rem' }}>
                      Hardware Biometrics
                    </span>
                  </div>
                  <p className="text-secondary" style={{ margin: 0, fontSize: '0.875rem' }}>
                    Authenticate securely using Touch ID, Face ID, Windows Hello, or your platform security key.
                    Your biometric scan never leaves your device hardware.
                  </p>
                </div>

                <div>
                  <label htmlFor="passkey-email" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                    Account Email (Optional)
                  </label>
                  <input
                    id="passkey-email"
                    type="email"
                    autoComplete="username webauthn"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="aarav.sharma@example.com"
                  />
                </div>

                <button
                  type="button"
                  className="btn"
                  onClick={handlePasskeyLogin}
                  disabled={isSubmitting}
                  style={{ width: '100%', marginTop: '0.5rem' }}
                >
                  <Key size={18} aria-hidden="true" />
                  <span>{isSubmitting ? 'Verifying Passkey...' : 'Use Device Passkey'}</span>
                </button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
