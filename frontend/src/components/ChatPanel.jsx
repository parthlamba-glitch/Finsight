import React, { useState } from 'react';
import { Volume2, VolumeX, Send, Mic, Square, Sparkles } from 'lucide-react';
import VoiceOrb from './VoiceOrb';

/**
 * ChatPanel Component
 * FinSight's Visual Centerpiece: Conversational Voice AI Copilot.
 * Dedicated high-prominence surface with acoustic orb, state indicators,
 * spoken response card, and quick query pills.
 */
export default function ChatPanel({
  onQuerySubmit,
  isProcessing,
  answerText,
  onReplay,
  isSpeaking,
  stopSpeaking,
  isListening,
  onStartListening,
  onStopListening,
}) {
  const [textInput, setTextInput] = useState('');

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

  const handleTextSubmit = (e) => {
    e.preventDefault();
    const query = textInput.trim();
    if (!query || isProcessing) return;
    setTextInput('');
    if (isSpeaking) stopSpeaking();
    onQuerySubmit(query);
  };

  const getStatusHeading = () => {
    if (isProcessing) return 'Thinking & Analyzing Ledger...';
    if (isSpeaking) return 'FinSight is Speaking...';
    if (isListening) return 'Listening... Speak Your Question';
    return 'Ask FinSight Anything About Your Money';
  };

  const QUICK_PROMPTS = [
    { label: 'Food spending last month', query: 'How much did I spend on food last month?' },
    { label: 'Can I afford ₹8,000 headphones?', query: 'Can I afford to buy headphones for ₹8,000?' },
    { label: 'Emergency Fund projection', query: 'When will I finish my Emergency Fund if I save ₹15,000 a month?' },
    { label: 'Show financial insights', query: 'Show me my financial insights and trends' },
  ];

  return (
    <section
      className="copilot-centerpiece"
      aria-label="FinSight Conversational Voice Copilot"
    >
      {/* 1. Header & Section Label */}
      <div style={{ position: 'relative', zIndex: 2 }}>
        <p className="copilot-tagline">
          Voice Intelligence Layer
        </p>
        <h2 className="copilot-title">
          FinSight Voice Copilot
        </h2>
      </div>

      {/* 2. Central Prominent Acoustic Orb */}
      <div style={{ margin: '0.75rem 0', position: 'relative', zIndex: 2 }}>
        <VoiceOrb
          isListening={isListening}
          isProcessing={isProcessing}
          isSpeaking={isSpeaking}
        />
      </div>

      {/* 3. Live State Indicator */}
      <div className="copilot-status-indicator" style={{ position: 'relative', zIndex: 2 }}>
        <p
          className="text-body"
          style={{
            margin: 0,
            fontWeight: 600,
            fontSize: '1.05rem',
            color: isListening
              ? 'var(--fs-accent-bright)'
              : isProcessing
              ? 'var(--fs-text)'
              : 'var(--fs-text-secondary)',
          }}
          aria-live="polite"
        >
          {getStatusHeading()}
        </p>
      </div>

      {/* 4. Large Primary Voice Control Trigger */}
      <div className="copilot-trigger-zone" style={{ position: 'relative', zIndex: 2 }}>
        <button
          type="button"
          className="btn btn-voice"
          onClick={handleToggleMic}
          disabled={isProcessing}
          style={{
            backgroundColor: isListening ? 'var(--fs-danger)' : 'var(--fs-accent)',
            color: isListening ? '#FFFFFF' : 'var(--fs-bg)',
            boxShadow: isListening ? '0 0 32px rgba(224, 108, 117, 0.45)' : '0 4px 24px rgba(141, 219, 146, 0.35)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.75rem',
            cursor: isProcessing ? 'wait' : 'pointer',
          }}
          aria-pressed={isListening}
          aria-label={isListening ? 'Stop listening to microphone' : 'Start speaking with FinSight Copilot'}
        >
          {isListening ? (
            <>
              <Square size={22} aria-hidden="true" />
              <span>Stop Listening</span>
            </>
          ) : (
            <>
              <Mic size={24} aria-hidden="true" />
              <span>Tap to Speak</span>
            </>
          )}
        </button>
      </div>

      {/* 5. Polished Response Surface (When Answer Exists) */}
      {answerText && !isListening && !isProcessing && (
        <div
          className="copilot-answer-panel"
          role="region"
          aria-label="FinSight Spoken Answer"
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '0.85rem' }}>
            <Sparkles size={16} color="var(--fs-accent)" aria-hidden="true" />
            <span className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '1px', fontWeight: 700, color: 'var(--fs-accent)' }}>
              Deterministic Ledger Answer
            </span>
          </div>

          <p className="copilot-answer-text">
            {answerText}
          </p>

          <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onReplay}
              style={{ minHeight: '38px', padding: '6px 14px', fontSize: '13px' }}
              aria-label="Replay spoken answer audio"
            >
              <Volume2 size={15} color="var(--fs-accent)" aria-hidden="true" />
              <span>Replay Audio</span>
            </button>

            {isSpeaking && (
              <button
                type="button"
                className="btn btn-danger"
                onClick={stopSpeaking}
                style={{ minHeight: '38px', padding: '6px 14px', fontSize: '13px' }}
                aria-label="Stop audio voice playback"
              >
                <VolumeX size={15} aria-hidden="true" />
                <span>Stop Speaking</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* 6. Accessible Keyboard Query Input */}
      <form
        onSubmit={handleTextSubmit}
        style={{
          display: 'flex',
          gap: '0.5rem',
          maxWidth: '560px',
          width: '100%',
          margin: '0.75rem 0',
          position: 'relative',
          zIndex: 2,
        }}
        role="search"
        aria-label="Type question for FinSight"
      >
        <label htmlFor="copilot-input" className="sr-only">
          Ask a financial question
        </label>
        <input
          id="copilot-input"
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Or type a question (e.g. 'Can I afford 5k?')..."
          disabled={isProcessing}
          style={{
            backgroundColor: 'var(--fs-bg)',
            border: '1px solid var(--fs-border)',
            borderRadius: 'var(--fs-radius-md)',
            padding: '12px 16px',
            fontSize: '14px',
          }}
        />
        <button
          type="submit"
          className="btn btn-secondary"
          disabled={isProcessing || !textInput.trim()}
          style={{ minHeight: '46px', padding: '0 16px' }}
          aria-label="Submit financial query"
        >
          <Send size={16} aria-hidden="true" />
        </button>
      </form>

      {/* 7. Quick Inquiry Pills */}
      {!isListening && !isProcessing && !isSpeaking && !answerText && (
        <div style={{ position: 'relative', zIndex: 2 }}>
          <p
            className="text-meta"
            style={{
              textTransform: 'uppercase',
              letterSpacing: '1px',
              fontWeight: 600,
              color: 'var(--fs-text-muted)',
              marginBottom: '0.75rem',
            }}
          >
            Suggested Ledger Inquiries
          </p>
          <div className="copilot-quick-pills">
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="quick-pill-btn"
                onClick={() => onQuerySubmit(prompt.query)}
              >
                "{prompt.label}"
              </button>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
