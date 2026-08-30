import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSpeech } from '../hooks/useSpeech';
import VoiceOrb from '../components/VoiceOrb';

export default function Login() {
  const navigate = useNavigate();
  const [isStarted, setIsStarted] = useState(false);
  const [authStatus, setAuthStatus] = useState('');

  const { speak, startListening, isListening, isSpeaking, isProcessing } = useSpeech((transcript) => {
    const lowerQuery = transcript.toLowerCase();
    
    if (lowerQuery.includes('google')) {
      handleAuth('Google');
    } else if (lowerQuery.includes('biometric')) {
      handleAuth('Biometric');
    } else if (lowerQuery.includes('open my account') || lowerQuery.includes('log me in') || lowerQuery.includes('sign in')) {
      handleAuth('Voice Secret Phrase');
    } else {
      speak("I didn't catch that. You can say Google, Biometric, or 'Open my account' to sign in.", () => {
        startListening();
      });
    }
  });

  const handleStart = () => {
    if (!isStarted) {
      setIsStarted(true);
      speak("Welcome to FinSight. How would you like to sign in? You can say Google, biometric, or another sign-in option.", () => {
        startListening();
      });
    }
  };

  const handleAuth = (method) => {
    setAuthStatus(`Opening ${method} authentication...`);
    speak(`Opening ${method} authentication. Welcome back!`, () => {
      navigate('/dashboard');
    });
  };

  const getStatusText = () => {
    if (authStatus) return authStatus;
    if (isListening) return "Listening...";
    if (isProcessing) return "Understanding...";
    if (isSpeaking) return "Speaking...";
    if (!isStarted) return "Tap anywhere to begin";
    return '"How would you like to sign in today?"';
  };

  return (
    <div 
      className="login-container" 
      onClick={!isStarted ? handleStart : undefined}
      onKeyDown={!isStarted ? (e) => { if (e.key === 'Enter' || e.key === ' ') handleStart(); } : undefined}
      tabIndex={!isStarted ? "0" : undefined}
      role={!isStarted ? "button" : undefined}
      aria-label={!isStarted ? "Tap anywhere or press Enter to start FinSight voice interface." : undefined}
    >
      {/* HEADER: Top Logo */}
      <header className="login-header">
        <h1 className="text-section-heading color-primary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', letterSpacing: '2px' }}>
          ◉ FIN•SIGHT
        </h1>
        <div className="text-secondary" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Accessibility ♿
        </div>
      </header>

      {/* CONTENT: Text and Card Side-by-Side (Desktop) or Stacked (Mobile) */}
      <div className="login-content">
        
        {/* TEXT AREA */}
        <div className="login-text-area">
          <h2 className="text-hero" style={{ marginBottom: '1.5rem' }}>
            YOUR MONEY,<br/>UNDERSTOOD.
          </h2>
          <p className="text-body color-muted" style={{ fontSize: '1.1rem' }}>
            An accessible financial copilot<br/>
            that listens, explains, protects<br/>
            and helps you decide.
          </p>
        </div>

        {/* AUTH CARD AREA */}
        <main className="login-card-area">
          <div className="card flex-col gap-6" style={{ width: '100%', textAlign: 'center', zIndex: 10 }}>
            
            <div style={{ margin: '1rem 0' }}>
              <VoiceOrb isListening={isListening} isProcessing={isProcessing} isSpeaking={isSpeaking || (!isStarted)} />
            </div>
            
            <div>
              <h3 className="text-card-heading color-primary">Welcome to FinSight</h3>
              <p className="text-body" style={{ marginTop: '1rem', fontStyle: 'italic', minHeight: '48px' }} aria-live="polite">
                {getStatusText()}
              </p>
            </div>
            
            <div className="flex-col gap-4" style={{ marginTop: '1rem' }}>
              <button className="btn" onClick={() => handleAuth('Google')} disabled={!!authStatus || !isStarted}>
                Continue with Google
              </button>
              <button className="btn btn-secondary" onClick={() => handleAuth('Biometric')} disabled={!!authStatus || !isStarted}>
                Use device biometrics
              </button>
              <button className="btn btn-secondary" onClick={() => handleAuth('Other')} disabled={!!authStatus || !isStarted} style={{ border: 'none' }}>
                Other options
              </button>
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
