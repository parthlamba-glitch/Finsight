import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { Key, ShieldCheck, UserCheck, AlertCircle, ArrowRight, Mic } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { useSpeech } from '../hooks/useSpeech';
import VoiceOrb from '../components/VoiceOrb';
import StatusBadge from '../components/StatusBadge';

/**
 * Login Page Component
 * Ultra-premium fintech authentication surface with FIDO2 passkeys,
 * email/password auth, accessibility preferences, and voice navigation.
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

  // Accessibility Preferences for Signup
  const [highContrast, setHighContrast] = useState(false);
  const [screenReaderOptimized, setScreenReaderOptimized] = useState(true);

  const formRef = useRef(null);

  // Voice transcript handler callback reference
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
    setStatusMessage('Signing in...');
    clearError();

    try {
      await login(email, password);
      speak('Signed in successfully. Welcome to your financial dashboard.', () => {
        navigate('/dashboard');
      });
    } catch (err) {
      const msg = err.message || 'Login failed. Please check your credentials.';
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
    setStatusMessage('Initiating device passkey authentication...');
    clearError();

    try {
      await loginWithPasskey(email || null);
      speak('Passkey verified successfully. Welcome back.', () => {
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
    if (isListening) return 'Listening...';
    if (isProcessing) return 'Understanding voice command...';
    if (isSpeaking) return 'Speaking...';
    if (!isStarted) return 'Click anywhere to enable voice navigation';
    return '"How would you like to sign in today?"';
  };

  return (
    <div
      className="login-container"
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
      aria-label={!isStarted ? 'Tap anywhere or press Enter to start FinSight voice interface.' : undefined}
      style={{
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'space-between',
        padding: '2rem 1.5rem',
        maxWidth: '1200px',
        margin: '0 auto',
      }}
    >
      {/* 1. TOP BRAND HEADER */}
      <header
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          paddingBottom: '1rem',
          borderBottom: '1px solid var(--fs-border-subtle, #142E25)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <span
            style={{
              width: '10px',
              height: '10px',
              borderRadius: '50%',
              backgroundColor: 'var(--fs-accent, #8DDB92)',
              boxShadow: '0 0 12px var(--fs-accent, #8DDB92)',
              display: 'inline-block',
            }}
            aria-hidden="true"
          />
          <h1
            className="text-section-heading"
            style={{
              letterSpacing: '1.5px',
              fontSize: '1.15rem',
              color: 'var(--fs-text, #F5F4EC)',
              margin: 0,
              textTransform: 'uppercase',
            }}
          >
            FIN•SIGHT
          </h1>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          <StatusBadge variant="success" icon={<ShieldCheck size={14} />}>
            WCAG 2.2 AAA
          </StatusBadge>
        </div>
      </header>

      {/* 2. MAIN TWO-COLUMN CONTENT */}
      <div
        className="login-content"
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))',
          gap: '3rem',
          alignItems: 'center',
          margin: '3rem 0',
        }}
      >
        {/* Left Column: Brand & Value Proposition */}
        <div className="login-text-area" style={{ maxWidth: '520px' }}>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
            <StatusBadge variant="neutral">Financial Copilot</StatusBadge>
            <StatusBadge variant="success" icon={<Mic size={12} />}>Voice-First</StatusBadge>
          </div>

          <h2
            className="text-hero"
            style={{
              fontSize: 'clamp(2.5rem, 5vw, 3.5rem)',
              lineHeight: 1.08,
              marginBottom: '1.5rem',
              color: 'var(--fs-text, #F5F4EC)',
            }}
          >
            Your money,
            <br />
            <span style={{ color: 'var(--fs-accent, #8DDB92)' }}>understood.</span>
          </h2>

          <p
            className="text-body"
            style={{
              fontSize: '1.125rem',
              lineHeight: 1.6,
              color: 'var(--fs-text-secondary, #AAB8B1)',
              marginBottom: '2rem',
            }}
          >
            An accessibility-first financial copilot designed around independence.
            Listen to your balances, verify suspicious payment links, and make decisions with deterministic precision.
          </p>

          {/* Voice Prompt Helper Box */}
          <div
            className="card card-elevated"
            style={{
              padding: '1.25rem',
              border: '1px solid var(--fs-border-hover, #2B5748)',
              backgroundColor: 'var(--fs-surface-card, #0F251E)',
            }}
          >
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 600, marginBottom: '0.5rem' }}>
              Voice Navigation Prompt
            </p>
            <p className="text-body" style={{ color: 'var(--fs-accent-bright, #A7E8A5)', fontStyle: 'italic', margin: 0 }}>
              "You can say 'Sign in', 'Create account', or 'Use passkey'."
            </p>
          </div>
        </div>

        {/* Right Column: Authentication Card */}
        <main className="login-card-area">
          <div
            className="card card-hero"
            style={{
              width: '100%',
              maxWidth: '460px',
              margin: '0 auto',
              padding: '2.25rem 2rem',
              borderRadius: 'var(--fs-radius-modal, 20px)',
            }}
          >
            {/* Acoustic Orb Indicator */}
            <div style={{ marginBottom: '0.5rem' }}>
              <VoiceOrb
                isListening={isListening}
                isProcessing={isProcessing}
                isSpeaking={isSpeaking || !isStarted}
              />
            </div>

            {/* Title & Live Status */}
            <div style={{ textAlign: 'center', marginBottom: '1.5rem' }}>
              <h3 className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', fontSize: '1.35rem' }}>
                {mode === 'signup' ? 'Create Your Account' : mode === 'passkey' ? 'Device Passkey Sign In' : 'Welcome Back'}
              </h3>
              <p
                className="text-secondary"
                style={{
                  marginTop: '0.5rem',
                  fontSize: '0.925rem',
                  minHeight: '24px',
                  color: authError ? 'var(--fs-danger-bright, #F08D95)' : 'var(--fs-text-secondary, #AAB8B1)',
                }}
                aria-live="polite"
              >
                {getStatusText()}
              </p>
            </div>

            {/* Mode Switcher Tabs */}
            <div
              role="tablist"
              aria-label="Authentication Mode Selection"
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(3, 1fr)',
                gap: '0.35rem',
                backgroundColor: 'var(--fs-bg, #071510)',
                padding: '4px',
                borderRadius: 'var(--fs-radius-md, 14px)',
                marginBottom: '1.75rem',
                border: '1px solid var(--fs-border, #1B382E)',
              }}
            >
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'login'}
                className="btn btn-secondary"
                style={{
                  minHeight: '38px',
                  padding: '8px',
                  fontSize: '0.85rem',
                  backgroundColor: mode === 'login' ? 'var(--fs-surface-elevated, #132D24)' : 'transparent',
                  color: mode === 'login' ? 'var(--fs-accent, #8DDB92)' : 'var(--fs-text-secondary, #AAB8B1)',
                  border: mode === 'login' ? '1px solid var(--fs-border-focus, #8DDB92)' : 'none',
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
                  minHeight: '38px',
                  padding: '8px',
                  fontSize: '0.85rem',
                  backgroundColor: mode === 'signup' ? 'var(--fs-surface-elevated, #132D24)' : 'transparent',
                  color: mode === 'signup' ? 'var(--fs-accent, #8DDB92)' : 'var(--fs-text-secondary, #AAB8B1)',
                  border: mode === 'signup' ? '1px solid var(--fs-border-focus, #8DDB92)' : 'none',
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
                  minHeight: '38px',
                  padding: '8px',
                  fontSize: '0.85rem',
                  backgroundColor: mode === 'passkey' ? 'var(--fs-surface-elevated, #132D24)' : 'transparent',
                  color: mode === 'passkey' ? 'var(--fs-accent, #8DDB92)' : 'var(--fs-text-secondary, #AAB8B1)',
                  border: mode === 'passkey' ? '1px solid var(--fs-border-focus, #8DDB92)' : 'none',
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

            {/* Error Banner */}
            {authError && (
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.6rem',
                  padding: '10px 14px',
                  backgroundColor: 'var(--fs-danger-surface, rgba(224, 108, 117, 0.12))',
                  border: '1px solid var(--fs-danger-border, rgba(224, 108, 117, 0.35))',
                  borderRadius: 'var(--fs-radius-sm, 8px)',
                  marginBottom: '1.25rem',
                  color: 'var(--fs-danger-bright, #F08D95)',
                  fontSize: '0.9rem',
                }}
                role="alert"
              >
                <AlertCircle size={18} aria-hidden="true" />
                <span>{authError}</span>
              </div>
            )}

            {/* 3. AUTH FORMS */}
            <div>
              {/* MODE 1: Standard Password Login */}
              {mode === 'login' && (
                <form onSubmit={handlePasswordLogin} className="flex-col gap-4" ref={formRef} tabIndex={-1}>
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
                    style={{ marginTop: '0.5rem', width: '100%' }}
                  >
                    <span>{isSubmitting ? 'Signing In...' : 'Sign In'}</span>
                    <ArrowRight size={18} aria-hidden="true" />
                  </button>

                  <div style={{ position: 'relative', margin: '1rem 0', textAlign: 'center' }}>
                    <div style={{ position: 'absolute', top: '50%', left: 0, right: 0, height: '1px', backgroundColor: 'var(--fs-border, #1B382E)' }} />
                    <span style={{ position: 'relative', backgroundColor: 'var(--fs-surface-card, #0F251E)', padding: '0 12px', fontSize: '12px', color: 'var(--fs-text-muted, #71817A)', textTransform: 'uppercase' }}>
                      Fast & Biometric
                    </span>
                  </div>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handlePasskeyLogin}
                    disabled={isSubmitting}
                    style={{ width: '100%' }}
                  >
                    <Key size={18} aria-hidden="true" />
                    <span>Sign In with Device Passkey</span>
                  </button>
                </form>
              )}

              {/* MODE 2: Registration / Signup */}
              {mode === 'signup' && (
                <form onSubmit={handleSignupSubmit} className="flex-col gap-4" ref={formRef} tabIndex={-1}>
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

                  {/* Accessibility Preferences */}
                  <fieldset
                    style={{
                      border: '1px solid var(--fs-border, #1B382E)',
                      borderRadius: 'var(--fs-radius-md, 14px)',
                      padding: '12px 14px',
                      backgroundColor: 'var(--fs-bg, #071510)',
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
                      <span className="text-body" style={{ fontSize: '0.9rem' }}>
                        Screen reader announcements enabled
                      </span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '10px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={highContrast}
                        onChange={(e) => setHighContrast(e.target.checked)}
                      />
                      <span className="text-body" style={{ fontSize: '0.9rem' }}>
                        High contrast theme (WCAG AAA)
                      </span>
                    </label>
                  </fieldset>

                  <button
                    type="submit"
                    className="btn"
                    disabled={isSubmitting}
                    style={{ marginTop: '0.5rem', width: '100%' }}
                  >
                    <UserCheck size={18} aria-hidden="true" />
                    <span>{isSubmitting ? 'Creating Account...' : 'Create Account'}</span>
                  </button>
                </form>
              )}

              {/* MODE 3: Dedicated Passkey Sign In */}
              {mode === 'passkey' && (
                <div className="flex-col gap-4">
                  <div
                    style={{
                      backgroundColor: 'var(--fs-bg, #071510)',
                      border: '1px solid var(--fs-border, #1B382E)',
                      borderRadius: 'var(--fs-radius-md, 14px)',
                      padding: '1rem',
                      lineHeight: 1.55,
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.5rem' }}>
                      <Key size={18} color="var(--fs-accent, #8DDB92)" aria-hidden="true" />
                      <span style={{ fontWeight: 600, color: 'var(--fs-text, #F5F4EC)', fontSize: '0.95rem' }}>
                        Cryptographic Device Biometrics
                      </span>
                    </div>
                    <p className="text-secondary" style={{ margin: 0, fontSize: '0.875rem' }}>
                      Sign in seamlessly using Touch ID, Face ID, Windows Hello, or your platform security key.
                      Your device handles biometric verification directly; FinSight stores only cryptographic public keys.
                    </p>
                  </div>

                  <div>
                    <label htmlFor="passkey-email" className="text-secondary" style={{ display: 'block', marginBottom: '6px', fontWeight: 500 }}>
                      Email (optional for autofill discovery)
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
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* 3. ACCESSIBILITY PILLARS FOOTER */}
      <footer
        className="login-footer"
        style={{
          display: 'flex',
          justifyContent: 'center',
          gap: '2.5rem',
          color: 'var(--fs-text-muted, #71817A)',
          fontWeight: 600,
          letterSpacing: '1.5px',
          fontSize: '0.85rem',
          flexWrap: 'wrap',
          borderTop: '1px solid var(--fs-border-subtle, #142E25)',
          paddingTop: '1.5rem',
        }}
      >
        <span>1. ACCESS</span>
        <span>2. UNDERSTAND</span>
        <span>3. PROTECT</span>
        <span>4. DECIDE</span>
      </footer>
    </div>
  );
}
