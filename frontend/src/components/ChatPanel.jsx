import React, { useState } from 'react';
import { Volume2, VolumeX, Send, Mic, Square } from 'lucide-react';
import VoiceOrb from './VoiceOrb';

/**
 * ChatPanel Component
 * Visual centerpiece for FinSight's Conversational AI Copilot.
 * Supports spoken audio, Web Speech API, quick prompt pills, and accessible keyboard entry.
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

  const getStatusText = () => {
    if (isProcessing) return 'Thinking and analyzing your financial ledger...';
    if (isSpeaking) return 'FinSight is answering...';
    if (isListening) return "Listening... Speak your question now.";
    return 'Ask anything about your money';
  };

  const QUICK_PROMPTS = [
    { label: 'Food spending last month', query: 'How much did I spend on food last month?' },
    { label: 'Can I afford ₹8,000 headphones?', query: 'Can I afford to buy headphones for ₹8,000?' },
    { label: 'Emergency Fund projection', query: 'When will I finish my Emergency Fund if I save ₹15,000 a month?' },
    { label: 'Financial insights & trends', query: 'Show me my financial insights' },
  ];

  return (
    <section
      className="card card-hero flex-col gap-6"
      aria-label="FinSight Conversational Copilot"
      style={{
        textAlign: 'center',
        padding: '2.5rem 1.5rem',
        position: 'relative',
        overflow: 'hidden',
      }}
    >
      {/* Copilot Header */}
      <div>
        <p
          className="text-meta"
          style={{
            textTransform: 'uppercase',
            letterSpacing: '1.5px',
            fontWeight: 700,
            color: 'var(--fs-accent, #8DDB92)',
            marginBottom: '0.25rem',
          }}
        >
          Intelligence Layer
        </p>
        <h2
          className="text-section-heading"
          style={{ color: 'var(--fs-text, #F5F4EC)' }}
        >
          FinSight Copilot
        </h2>
      </div>

      {/* Acoustic Voice Orb */}
      <div style={{ margin: '0.5rem 0' }}>
        <VoiceOrb
          isListening={isListening}
          isProcessing={isProcessing}
          isSpeaking={isSpeaking}
        />
      </div>

      {/* Accessible Live Status Heading */}
      <div style={{ minHeight: '32px' }}>
        <p
          className="text-body"
          style={{
            fontWeight: 500,
            color: isListening ? 'var(--fs-accent-bright, #A7E8A5)' : 'var(--fs-text-secondary, #AAB8B1)',
          }}
          aria-live="polite"
        >
          {getStatusText()}
        </p>
      </div>

      {/* Spoken Answer Box */}
      {answerText && !isListening && !isProcessing && (
        <div
          className="card-elevated"
          style={{
            textAlign: 'left',
            margin: '0.5rem 0',
            border: '1px solid var(--fs-border-hover, #2B5748)',
            backgroundColor: 'var(--fs-surface-elevated, #132D24)',
          }}
          role="region"
          aria-label="Copilot Answer"
        >
          <p
            className="text-body"
            style={{
              fontSize: '1.05rem',
              lineHeight: 1.6,
              marginBottom: '1.25rem',
              color: 'var(--fs-text, #F5F4EC)',
            }}
          >
            {answerText}
          </p>

          <div className="flex-row gap-3" style={{ flexWrap: 'wrap' }}>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={onReplay}
              style={{
                minHeight: '40px',
                padding: '8px 16px',
                fontSize: '14px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}
              aria-label="Replay spoken answer"
            >
              <Volume2 size={16} aria-hidden="true" />
              <span>Replay Voice</span>
            </button>

            {isSpeaking && (
              <button
                type="button"
                className="btn btn-danger"
                onClick={stopSpeaking}
                style={{
                  minHeight: '40px',
                  padding: '8px 16px',
                  fontSize: '14px',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.5rem',
                }}
                aria-label="Stop audio narration"
              >
                <VolumeX size={16} aria-hidden="true" />
                <span>Stop Speaking</span>
              </button>
            )}
          </div>
        </div>
      )}

      {/* Primary Voice Action Trigger */}
      <div className="flex-center" style={{ marginTop: '0.5rem' }}>
        <button
          type="button"
          className="btn btn-voice"
          onClick={handleToggleMic}
          style={{
            backgroundColor: isListening ? 'var(--fs-danger, #E06C75)' : 'var(--fs-accent, #8DDB92)',
            color: isListening ? '#FFFFFF' : 'var(--fs-bg, #071510)',
            display: 'inline-flex',
            alignItems: 'center',
            gap: '0.75rem',
            padding: '16px 36px',
          }}
          aria-pressed={isListening}
          aria-label={isListening ? 'Stop listening to microphone' : 'Start speaking with microphone'}
        >
          {isListening ? (
            <>
              <Square size={20} aria-hidden="true" />
              <span>Stop Listening</span>
            </>
          ) : (
            <>
              <Mic size={22} aria-hidden="true" />
              <span>Start Speaking</span>
            </>
          )}
        </button>
      </div>

      {/* Optional Keyboard / Text Input */}
      <form
        onSubmit={handleTextSubmit}
        className="flex-row gap-2"
        style={{
          maxWidth: '560px',
          width: '100%',
          margin: '0.75rem auto 0 auto',
        }}
        role="search"
        aria-label="Type a question for FinSight Copilot"
      >
        <label htmlFor="copilot-text-input" className="sr-only">
          Ask a financial question
        </label>
        <input
          id="copilot-text-input"
          type="text"
          value={textInput}
          onChange={(e) => setTextInput(e.target.value)}
          placeholder="Or type a question (e.g. 'Can I afford 5k?')..."
          disabled={isProcessing}
          style={{
            backgroundColor: 'var(--fs-surface, #0D211B)',
            padding: '12px 16px',
            fontSize: '15px',
          }}
        />
        <button
          type="submit"
          className="btn btn-secondary"
          disabled={isProcessing || !textInput.trim()}
          style={{ minHeight: '48px', padding: '0 18px' }}
          aria-label="Submit financial question"
        >
          <Send size={18} aria-hidden="true" />
        </button>
      </form>

      {/* Quick Prompts */}
      {!isListening && !isProcessing && !isSpeaking && !answerText && (
        <div style={{ marginTop: '1.5rem', textAlign: 'center' }}>
          <p
            className="text-meta"
            style={{
              marginBottom: '0.75rem',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              fontWeight: 600,
            }}
          >
            Suggested Inquiries
          </p>
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              justifyContent: 'center',
              gap: '0.5rem',
            }}
          >
            {QUICK_PROMPTS.map((prompt, idx) => (
              <button
                key={idx}
                type="button"
                className="btn btn-secondary"
                onClick={() => onQuerySubmit(prompt.query)}
                style={{
                  borderRadius: 'var(--fs-radius-full, 9999px)',
                  padding: '8px 16px',
                  fontSize: '13px',
                  minHeight: '38px',
                }}
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
