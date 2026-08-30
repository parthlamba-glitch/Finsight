import React from 'react';
import VoiceOrb from './VoiceOrb';

export default function ChatPanel({ onQuerySubmit, isProcessing, answerText, onReplay, isSpeaking, stopSpeaking, isListening, onStartListening, onStopListening }) {
  const handleToggleMic = () => {
    if (isListening) {
      onStopListening();
    } else {
      if (isSpeaking) {
        stopSpeaking();
      }
      onStartListening();
    }
  };

  const getStatusText = () => {
    if (isProcessing) return "Understanding your question...";
    if (isSpeaking) return "FinSight is answering...";
    if (isListening) return "I'm listening...";
    return "What would you like to know?";
  };

  return (
    <section className="card flex-col gap-6" aria-label="Ask FinSight" style={{ textAlign: 'center', padding: '3rem 2rem' }}>
      
      <div style={{ margin: '1rem 0' }}>
        <VoiceOrb isListening={isListening} isProcessing={isProcessing} isSpeaking={isSpeaking} />
      </div>

      <div style={{ minHeight: '40px' }}>
        <h2 className="text-section-heading color-primary" aria-live="polite">
          {getStatusText()}
        </h2>
      </div>

      {/* Answer box (only shown if there's an answer and we're not actively listening/processing) */}
      {answerText && !isListening && !isProcessing && (
        <div className="card-elevated animate-fade-in" style={{ textAlign: 'left', marginTop: '1rem' }}>
          <p className="text-body" style={{ marginBottom: '1.5rem' }}>{answerText}</p>
          <div className="flex-col gap-4">
            <button className="btn btn-secondary" onClick={onReplay} style={{ minHeight: '40px', padding: '8px 16px', fontSize: '14px' }}>
              🔊 Replay
            </button>
            {isSpeaking && (
              <button className="btn btn-secondary" onClick={stopSpeaking} style={{ minHeight: '40px', padding: '8px 16px', fontSize: '14px', color: 'var(--color-error)' }}>
                Stop Speaking
              </button>
            )}
          </div>
        </div>
      )}

      {/* The massive microphone button for sighted users / fallback */}
      <div style={{ marginTop: '1rem', display: 'flex', justifyContent: 'center' }}>
        <button 
          className="btn" 
          onClick={handleToggleMic}
          style={{ 
            borderRadius: '50px', 
            padding: '16px 32px',
            backgroundColor: isListening ? 'var(--color-error)' : 'var(--color-primary)',
            color: isListening ? 'white' : 'var(--color-bg)',
            minHeight: '64px',
            fontSize: '18px'
          }}
          aria-pressed={isListening}
          aria-label={isListening ? "Stop listening" : "Start speaking"}
        >
          {isListening ? '🛑 Stop listening' : '🎙 Start speaking'}
        </button>
      </div>

      {!isListening && !isProcessing && !isSpeaking && !answerText && (
        <div style={{ marginTop: '2.5rem', textAlign: 'center' }}>
          <p className="text-secondary" style={{ marginBottom: '1rem', fontSize: '0.9rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
            Try asking FinSight:
          </p>
          <div className="flex-col gap-2" style={{ alignItems: 'center' }}>
            <button className="btn btn-secondary" onClick={() => onQuerySubmit("Can I afford to buy headphones for ₹8,000?")} style={{ borderRadius: '20px', padding: '8px 16px', fontSize: '14px', width: 'fit-content' }}>
              "Can I afford headphones for ₹8,000?"
            </button>
            <button className="btn btn-secondary" onClick={() => onQuerySubmit("Show me my financial insights")} style={{ borderRadius: '20px', padding: '8px 16px', fontSize: '14px', width: 'fit-content' }}>
              "Show me my financial insights"
            </button>
            <button className="btn btn-secondary" onClick={() => onQuerySubmit("When will I finish my Emergency Fund if I save ₹15,000 a month?")} style={{ borderRadius: '20px', padding: '8px 16px', fontSize: '14px', width: 'fit-content' }}>
              "When will I finish my goal if I save ₹15,000?"
            </button>
            <button className="btn btn-secondary" onClick={() => onQuerySubmit("How much did I spend on food last month?")} style={{ borderRadius: '20px', padding: '8px 16px', fontSize: '14px', width: 'fit-content' }}>
              "How much did I spend on food last month?"
            </button>
          </div>
        </div>
      )}

    </section>
  );
}
