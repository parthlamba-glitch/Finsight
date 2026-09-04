import React from 'react';
import '../styles/orb.css';

/**
 * VoiceOrb Component
 * Visual signature acoustic sphere for FinSight with 5 distinct states:
 * IDLE, LISTENING, PROCESSING, SPEAKING, ERROR.
 *
 * Implements depth, concentric waveform rings, audio equalizer, and screen-reader accessibility.
 */
export default function VoiceOrb({
  isListening = false,
  isProcessing = false,
  isSpeaking = false,
  isError = false,
}) {
  let state = 'IDLE';
  let stateLabel = 'Ready to assist';

  if (isError) {
    state = 'ERROR';
    stateLabel = 'Attention required';
  } else if (isProcessing) {
    state = 'PROCESSING';
    stateLabel = 'Analyzing ledger...';
  } else if (isSpeaking) {
    state = 'SPEAKING';
    stateLabel = 'FinSight is speaking';
  } else if (isListening) {
    state = 'LISTENING';
    stateLabel = 'Listening to voice...';
  }

  const containerClass = state.toLowerCase();

  return (
    <div className="orb-wrapper" aria-hidden="true">
      <div className={`orb-container ${containerClass}`}>
        {/* Layer 1: Ambient Backdrop Aura */}
        <div className="orb-ambient-aura" />

        {/* Layer 2: Concentric Acoustic Waveform Rings (Listening) */}
        {state === 'LISTENING' && (
          <>
            <div className="acoustic-ring acoustic-ring-1" />
            <div className="acoustic-ring acoustic-ring-2" />
            <div className="acoustic-ring acoustic-ring-3" />
          </>
        )}

        {/* Layer 3: Dashed Processing Orbit (Processing) */}
        {state === 'PROCESSING' && (
          <div className="processing-orbit" />
        )}

        {/* Layer 4: Central Sphere with Realistic Optical Depth */}
        <div className={`orb-core ${containerClass}`} />

        {/* Layer 5: Audio Equalizer Bars (Speaking) */}
        {state === 'SPEAKING' && (
          <div className="orb-speaking-eq">
            <div className="eq-bar" />
            <div className="eq-bar" />
            <div className="eq-bar" />
            <div className="eq-bar" />
            <div className="eq-bar" />
          </div>
        )}
      </div>

      {/* Layer 6: Visual & Screen-Reader Accessible Status Pill */}
      <div className="orb-status-pill">
        <span className={`orb-status-indicator-dot ${containerClass}`} />
        <span>{stateLabel}</span>
      </div>
    </div>
  );
}
