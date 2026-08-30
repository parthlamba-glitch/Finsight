import React, { useState, useRef, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../hooks/useAuth';
import { useSpeech } from '../hooks/useSpeech';
import VoiceOrb from '../components/VoiceOrb';

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

  // Voice transcript handler callback reference to prevent immutability linter issues
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
      setStatusMessage('Please enter both email and password.');
      speak('Please enter both email and password.');
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
      setStatusMessage('Please fill in all required fields.');
      speak('Please fill in all required fields.');
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
    if (isProcessing) return 'Understanding...';
    if (isSpeaking) return 'Speaking...';
    if (!isStarted) return 'Tap anywhere or click to start voice navigation';
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
    >
      {/* HEADER: Top Logo */}
      <header className="login-header">
        <h1
          className="text-section-heading color-primary"
          style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', letterSpacing: '2px' }}
        >
          ◉ FIN•SIGHT
        </h1>
        <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Accessibility ♿
        </div>
      </header>

      {/* CONTENT */}
      <div className="login-content">
        {/* TEXT AREA */}
        <div className="login-text-area">
          <h2 className="text-hero" style={{ marginBottom: '1.5rem' }}>
            YOUR MONEY,
            <br />
            UNDERSTOOD.
          </h2>
          <p className="text-body color-muted" style={{ fontSize: '1.1rem' }}>
            An accessible financial copilot
            <br />
            that listens, explains, protects
            <br />
            and helps you decide.
          </p>
        </div>

        {/* AUTH CARD AREA */}
        <main className="login-card-area">
          <div className="card flex-col gap-6" style={{ width: '100%', textAlign: 'center', zIndex: 10 }}>
            <div style={{ margin: '1rem 0' }}>
              <VoiceOrb isListening={isListening} isProcessing={isProcessing} isSpeaking={isSpeaking || !isStarted} />
            </div>

            <div>
              <h3 className="text-card-heading color-primary">
                {mode === 'signup' ? 'Create FinSight Account' : 'Welcome to FinSight'}
              </h3>
              <p
                className="text-body"
                style={{
                  marginTop: '1rem',
                  fontStyle: 'italic',
                  minHeight: '48px',
                  color: authError ? 'var(--color-error)' : 'var(--color-text)',
                }}
                aria-live="polite"
              >
                {getStatusText()}
              </p>
            </div>

            {/* TAB SELECTOR */}
            <div
              role="tablist"
              aria-label="Authentication mode"
              style={{
                display: 'flex',
                justifyContent: 'center',
                gap: '0.5rem',
                borderBottom: '1px solid var(--color-border)',
                paddingBottom: '0.5rem',
              }}
            >
              <button
                type="button"
                role="tab"
                aria-selected={mode === 'login'}
                className={`btn btn-secondary ${mode === 'login' ? 'active' : ''}`}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  border: mode === 'login' ? '2px solid var(--color-primary)' : '1px solid transparent',
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
                className={`btn btn-secondary ${mode === 'signup' ? 'active' : ''}`}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  border: mode === 'signup' ? '2px solid var(--color-primary)' : '1px solid transparent',
                }}
                onClick={() => {
                  setMode('signup');
                  clearError();
                  setStatusMessage('');
                }}
              >
                Create Account
              </button>

              <button
                type="button"
                role="tab"
                aria-selected={mode === 'passkey'}
                className={`btn btn-secondary ${mode === 'passkey' ? 'active' : ''}`}
                style={{
                  padding: '8px 16px',
                  fontSize: '0.9rem',
                  border: mode === 'passkey' ? '2px solid var(--color-primary)' : '1px solid transparent',
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

            {/* FORM CONTAINER */}
            <div style={{ textAlign: 'left' }}>
              {mode === 'login' && (
                <form onSubmit={handlePasswordLogin} className="flex-col gap-4" ref={formRef} tabIndex={-1}>
                  <div>
                    <label htmlFor="login-email" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
                      Email Address
                    </label>
                    <input
                      id="login-email"
                      type="email"
                      required
                      autoComplete="username"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <div>
                    <label htmlFor="login-password" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
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
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <button
                    type="submit"
                    className="btn"
                    disabled={isSubmitting}
                    style={{ marginTop: '0.5rem', width: '100%', padding: '14px' }}
                  >
                    {isSubmitting ? 'Signing In...' : 'Sign In with Password'}
                  </button>

                  <button
                    type="button"
                    className="btn btn-secondary"
                    onClick={handlePasskeyLogin}
                    disabled={isSubmitting}
                    style={{ width: '100%', padding: '12px' }}
                  >
                    🔑 Sign In with Device Passkey
                  </button>
                </form>
              )}

              {mode === 'signup' && (
                <form onSubmit={handleSignupSubmit} className="flex-col gap-4" ref={formRef} tabIndex={-1}>
                  <div>
                    <label htmlFor="signup-name" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
                      Full Name
                    </label>
                    <input
                      id="signup-name"
                      type="text"
                      required
                      autoComplete="name"
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                      placeholder="Your Full Name"
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <div>
                    <label htmlFor="signup-email" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
                      Email Address
                    </label>
                    <input
                      id="signup-email"
                      type="email"
                      required
                      autoComplete="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com"
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <div>
                    <label htmlFor="signup-password" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
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
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <fieldset style={{ border: '1px solid var(--color-border)', borderRadius: '8px', padding: '10px' }}>
                    <legend className="text-secondary" style={{ fontSize: '0.85rem' }}>
                      Accessibility Preferences
                    </legend>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', marginBottom: '6px' }}>
                      <input
                        type="checkbox"
                        checked={screenReaderOptimized}
                        onChange={(e) => setScreenReaderOptimized(e.target.checked)}
                      />
                      <span className="text-body" style={{ fontSize: '0.9rem' }}>
                        Screen reader optimization
                      </span>
                    </label>
                    <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
                      <input
                        type="checkbox"
                        checked={highContrast}
                        onChange={(e) => setHighContrast(e.target.checked)}
                      />
                      <span className="text-body" style={{ fontSize: '0.9rem' }}>
                        High contrast display
                      </span>
                    </label>
                  </fieldset>

                  <button
                    type="submit"
                    className="btn"
                    disabled={isSubmitting}
                    style={{ marginTop: '0.5rem', width: '100%', padding: '14px' }}
                  >
                    {isSubmitting ? 'Creating Account...' : 'Create Account'}
                  </button>
                </form>
              )}

              {mode === 'passkey' && (
                <div className="flex-col gap-4">
                  <p className="text-body" style={{ fontSize: '0.95rem' }}>
                    Sign in securely with Windows Hello, Touch ID, Face ID, or your platform security key.
                  </p>
                  <div>
                    <label htmlFor="passkey-email" className="text-secondary" style={{ display: 'block', marginBottom: '4px' }}>
                      Email (optional for autofill)
                    </label>
                    <input
                      id="passkey-email"
                      type="email"
                      autoComplete="username webauthn"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="user@example.com (optional)"
                      className="input"
                      style={{
                        width: '100%',
                        padding: '12px',
                        borderRadius: '8px',
                        backgroundColor: 'var(--color-bg)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                      }}
                    />
                  </div>

                  <button
                    type="button"
                    className="btn"
                    onClick={handlePasskeyLogin}
                    disabled={isSubmitting}
                    style={{ width: '100%', padding: '14px' }}
                  >
                    {isSubmitting ? 'Verifying Passkey...' : '🔑 Use Device Passkey'}
                  </button>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>

      {/* FOOTER */}
      <footer className="login-footer">
        <span>ACCESS</span>
        <span>UNDERSTAND</span>
        <span>PROTECT</span>
        <span>DECIDE</span>
      </footer>
    </div>
  );
}
