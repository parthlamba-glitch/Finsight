import React from 'react';
import { Mic, Square, Loader } from 'lucide-react';

export default function VoiceInput({ 
  isListening, 
  isProcessing, 
  onStartListening, 
  onStopListening 
}) {
  return (
    <div className="voice-input-container flex-col flex-center gap-4">
      {/* Screen reader only live region for announcing states */}
      <div aria-live="polite" className="sr-only">
        {isListening ? "Listening. Speak your question." : 
         isProcessing ? "Understanding your question..." : ""}
      </div>
      
      <button
        onClick={isListening ? onStopListening : onStartListening}
        className={`btn btn-icon ${isListening ? 'listening' : ''}`}
        aria-label={isListening ? "Stop listening" : "Start listening"}
        disabled={isProcessing}
        style={{ 
          padding: '1rem',
          borderRadius: '50%',
          width: '80px',
          height: '80px',
          backgroundColor: isListening ? 'var(--color-error)' : 'var(--color-primary)'
        }}
      >
        {isListening ? <Square size={32} /> : <Mic size={32} />}
      </button>

      <div className="voice-status" aria-hidden="true" style={{ fontWeight: 'bold' }}>
        {isListening ? (
          <span className="flex-center gap-2"><Mic size={18} /> I'm listening...</span>
        ) : isProcessing ? (
          <span className="flex-center gap-2"><Loader size={18} className="spin" /> Understanding...</span>
        ) : (
          <span>🎙 ASK FINSIGHT</span>
        )}
      </div>
      
      <style>{`
        .spin { animation: spin 1s linear infinite; }
        @keyframes spin { 100% { transform: rotate(360deg); } }
      `}</style>
    </div>
  );
}
