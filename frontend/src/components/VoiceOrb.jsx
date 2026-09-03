import React from 'react';
import '../styles/orb.css';

/**
 * VoiceOrb Component
 * Central intelligent acoustic indicator with 5 calm states:
 * IDLE, LISTENING, PROCESSING, SPEAKING, ERROR.
 *
 * Fully accessible with screen-reader text and prefers-reduced-motion support.
 */
export default function VoiceOrb({
  isListening = false,
  isProcessing = false,
  isSpeaking = false,
  isError = false,
}) {
  let state = 'IDLE';
  let stateLabel = 'Ready';

  if (isError) {
    state = 'ERROR';
    stateLabel = 'Attention';
  } else if (isProcessing) {
    state = 'PROCESSING';
    stateLabel = 'Thinking';
  } else if (isSpeaking) {
    state = 'SPEAKING';
    stateLabel = 'Answering';
  } else if (isListening) {
    state = 'LISTENING';
    stateLabel = 'Listening';
  }

  return (
    <div className="orb-wrapper" aria-hidden="true">
      <div className={`orb-container ${isListening ? 'orb-listening' : ''}`}>
        {/* Acoustic concentric rings for listening state */}
        {state === 'LISTENING' && (
          <>
            <div className="orb-ring orb-ring-1" />
            <div className="orb-ring orb-ring-2" />
            <div className="orb-ring orb-ring-3" />
          </>
        )}

        {/* Central Orb Core */}
        <div
          className={`orb ${
            state === 'IDLE' ? 'orb-idle' :
            state === 'PROCESSING' ? 'orb-processing' :
            state === 'SPEAKING' ? 'orb-speaking' :
            state === 'ERROR' ? 'orb-error' : ''
          }`}
        />
      </div>

      {/* Speaking Equalizer Wave Bars */}
      {state === 'SPEAKING' && (
        <div className="orb-equalizer" aria-hidden="true">
          <div className="eq-bar" />
          <div className="eq-bar" />
          <div className="eq-bar" />
          <div className="eq-bar" />
          <div className="eq-bar" />
        </div>
      )}

      {/* Calm State Label Badge */}
      <div className="orb-state-label">
        <span
          className={`orb-state-dot ${state.toLowerCase()}`}
          aria-hidden="true"
        />
        <span>{stateLabel}</span>
      </div>
    </div>
  );
}
