import React from 'react';
import '../styles/orb.css';

export default function VoiceOrb({ isListening, isProcessing, isSpeaking }) {
  
  let state = 'IDLE';
  if (isListening) state = 'LISTENING';
  else if (isProcessing) state = 'PROCESSING';
  else if (isSpeaking) state = 'SPEAKING';

  return (
    <div className="orb-container" aria-hidden="true">
      <div className={`orb ${
        state === 'LISTENING' ? 'orb-listening' : 
        state === 'SPEAKING' ? 'orb-speaking' : ''
      }`} />
      
      {state === 'LISTENING' && (
        <div className="orb-trail">
          <span className="wave-dot">~</span>
          <span className="wave-dot">~</span>
          <span className="wave-dot">~</span>
        </div>
      )}
      
      {state === 'PROCESSING' && (
        <div className="orb-trail">
          <span className="wave-dot">.</span>
          <span className="wave-dot">.</span>
          <span className="wave-dot">.</span>
        </div>
      )}

      {state === 'SPEAKING' && (
        <div className="orb-trail" style={{ letterSpacing: '4px' }}>
          <span>)</span>
          <span>)</span>
          <span>)</span>
        </div>
      )}
    </div>
  );
}
