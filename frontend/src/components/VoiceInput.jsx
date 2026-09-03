import React from 'react';
import { Mic, Square, Loader } from 'lucide-react';

/**
 * VoiceInput Component
 * Accessible, high-contrast primary voice trigger control.
 * Minimum 64px interactive target with clear focus and aria announcements.
 */
export default function VoiceInput({ 
  isListening, 
  isProcessing, 
  onStartListening, 
  onStopListening 
}) {
  return (
    <div className="voice-input-container flex-col flex-center gap-3">
      {/* Screen reader only live region for announcing voice states */}
      <div aria-live="polite" className="sr-only">
        {isListening ? "Listening. Speak your question now." : 
         isProcessing ? "FinSight is processing your question." : "Voice copilot ready."}
      </div>
      
      <button
        type="button"
        onClick={isListening ? onStopListening : onStartListening}
        className="btn btn-voice"
        aria-label={isListening ? "Stop listening to speech" : "Start speaking to FinSight Copilot"}
        aria-pressed={isListening}
        disabled={isProcessing}
        style={{ 
          borderRadius: 'var(--fs-radius-full, 9999px)',
          width: '72px',
          height: '72px',
          backgroundColor: isListening ? 'var(--fs-danger, #E06C75)' : 'var(--fs-accent, #8DDB92)',
          color: isListening ? '#FFFFFF' : 'var(--fs-bg, #071510)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          boxShadow: isListening 
            ? '0 0 24px rgba(224, 108, 117, 0.4)' 
            : '0 4px 20px rgba(141, 219, 146, 0.3)',
          border: 'none',
          cursor: isProcessing ? 'wait' : 'pointer',
        }}
      >
        {isListening ? (
          <Square size={28} aria-hidden="true" />
        ) : isProcessing ? (
          <Loader size={28} className="spin" aria-hidden="true" />
        ) : (
          <Mic size={28} aria-hidden="true" />
        )}
      </button>

      <div className="text-meta" aria-hidden="true" style={{ fontWeight: 600, letterSpacing: '1px', textTransform: 'uppercase' }}>
        {isListening ? (
          <span style={{ color: 'var(--fs-danger-bright, #F08D95)' }}>Listening...</span>
        ) : isProcessing ? (
          <span style={{ color: 'var(--fs-accent, #8DDB92)' }}>Thinking...</span>
        ) : (
          <span style={{ color: 'var(--fs-text-secondary, #AAB8B1)' }}>Tap to Speak</span>
        )}
      </div>

      <style>{`
        .spin {
          animation: spin 1.2s linear infinite;
        }
        @keyframes spin {
          100% { transform: rotate(360deg); }
        }
        @media (prefers-reduced-motion: reduce) {
          .spin {
            animation: none !important;
          }
        }
      `}</style>
    </div>
  );
}
