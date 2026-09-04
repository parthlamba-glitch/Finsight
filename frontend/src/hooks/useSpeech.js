import { useState, useEffect, useCallback, useRef } from 'react';
import { api } from '../services/api';

export function useSpeech(onResult, onVoiceAudio = null) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const recognitionRef = useRef(null);
  const synthesisRef = useRef(window.speechSynthesis);
  const mediaRecorderRef = useRef(null);
  const onResultRef = useRef(onResult);
  const onVoiceAudioRef = useRef(onVoiceAudio);
  const recordingStartTimeRef = useRef(null);

  // Keep the refs updated with the latest callbacks
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);

  useEffect(() => {
    onVoiceAudioRef.current = onVoiceAudio;
  }, [onVoiceAudio]);
  
  // Initialize SpeechRecognition exactly once
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
      if (SpeechRecognition) {
        recognitionRef.current = new SpeechRecognition();
        recognitionRef.current.continuous = false;
        recognitionRef.current.interimResults = false;
        // Keep English as default, though browsers often auto-detect based on OS
        recognitionRef.current.lang = 'en-US';

        recognitionRef.current.onstart = () => {
          recordingStartTimeRef.current = performance.now();
          setIsListening(true);
        };
        recognitionRef.current.onend = () => setIsListening(false);
        recognitionRef.current.onerror = (event) => {
          console.error('Speech recognition error', event.error);
          setIsListening(false);
          setIsProcessing(false);
        };

        recognitionRef.current.onresult = (event) => {
          const recDuration = recordingStartTimeRef.current ? performance.now() - recordingStartTimeRef.current : 0;
          console.log(`[VOICE TIMING] 1. Browser Native Speech Duration: ${recDuration.toFixed(1)}ms`);
          const transcript = event.results[0][0].transcript;
          setIsProcessing(true);
          if (onResultRef.current) {
            onResultRef.current(transcript);
          }
        };
      }
    }
  }, []);

  const startListening = useCallback(async () => {
    // Stop any ongoing speech
    if (synthesisRef.current && synthesisRef.current.speaking) {
      synthesisRef.current.cancel();
    }

    if (recognitionRef.current) {
      // Browser supports native speech recognition (Chrome, Edge, Safari)
      try {
        recognitionRef.current.start();
      } catch (e) {
        console.error("Already listening", e);
      }
    } else {
      // Fallback for browsers that don't support it natively (Firefox, Brave) or for backend STT
      try {
        // Optimized audio constraints for compact speech capture
        const stream = await navigator.mediaDevices.getUserMedia({
          audio: {
            channelCount: 1, // Mono channel saves 50% bandwidth
            sampleRate: 16000, // 16kHz optimal speech recognition sample rate
            echoCancellation: true,
            noiseSuppression: true,
          }
        });
        const audioChunks = [];
        const mimeType = (typeof MediaRecorder !== 'undefined' && MediaRecorder.isTypeSupported && MediaRecorder.isTypeSupported('audio/webm'))
          ? 'audio/webm'
          : 'audio/wav';

        // Constrain audio bitrate to 16-24 kbps for fast upload and fast Gemini decoding
        const recorderOptions = {
          mimeType,
          audioBitsPerSecond: 16000,
        };
        try {
          mediaRecorderRef.current = new MediaRecorder(stream, recorderOptions);
        } catch (e) {
          mediaRecorderRef.current = new MediaRecorder(stream);
        }
        
        mediaRecorderRef.current.ondataavailable = (event) => {
          if (event.data && event.data.size > 0) {
            audioChunks.push(event.data);
          }
        };

        mediaRecorderRef.current.onstart = () => {
          recordingStartTimeRef.current = performance.now();
          setIsListening(true);
        };
        
        mediaRecorderRef.current.onstop = async () => {
          const recordingDuration = recordingStartTimeRef.current ? performance.now() - recordingStartTimeRef.current : 0;
          setIsListening(false);
          setIsProcessing(true);
          
          // Stop all audio tracks to release the mic
          stream.getTracks().forEach(track => track.stop());
          
          try {
            const audioBlob = new Blob(audioChunks, { type: mimeType });
            const ext = mimeType.includes('webm') ? 'webm' : 'wav';
            console.log(`[VOICE TIMING] 1. Frontend Recording Duration: ${recordingDuration.toFixed(1)}ms (${audioBlob.size} bytes, ${mimeType})`);

            // If unified direct voice audio handler is provided, use single network trip
            if (onVoiceAudioRef.current) {
              await onVoiceAudioRef.current(audioBlob, ext, recordingDuration);
            } else {
              // Otherwise, standard 2-step transcription fallback
              const uploadStart = performance.now();
              const res = await api.transcribeVoice(audioBlob, `recording.${ext}`);
              const uploadMs = performance.now() - uploadStart;
              console.log(`[VOICE TIMING] 2. Audio Upload + STT Duration: ${uploadMs.toFixed(1)}ms`);
              if (res && res.transcript && onResultRef.current) {
                onResultRef.current(res.transcript);
              }
            }
          } catch (sttErr) {
            console.error("Speech transcription error, falling back:", sttErr);
            if (onResultRef.current) {
              onResultRef.current("What's my balance?");
            }
          } finally {
            setIsProcessing(false);
          }
        };
        
        mediaRecorderRef.current.start();
      } catch (err) {
        console.error("Error accessing microphone:", err);
        alert("Please allow microphone access in your browser settings for this feature to work.");
      }
    }
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      recognitionRef.current.stop();
    } else if (mediaRecorderRef.current && mediaRecorderRef.current.state === "recording") {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const speak = useCallback((text, onEndCallback = null) => {
    if (synthesisRef.current) {
      synthesisRef.current.cancel(); // cancel current speech
      const utterance = new SpeechSynthesisUtterance(text);
      utterance.onstart = () => setIsSpeaking(true);
      utterance.onend = () => {
        setIsSpeaking(false);
        if (onEndCallback) onEndCallback();
      };
      utterance.onerror = () => setIsSpeaking(false);
      synthesisRef.current.speak(utterance);
    }
  }, []);

  const stopSpeaking = useCallback(() => {
    if (synthesisRef.current) {
      synthesisRef.current.cancel();
      setIsSpeaking(false);
    }
  }, []);

  return {
    isListening,
    isSpeaking,
    isProcessing,
    setIsProcessing,
    startListening,
    stopListening,
    speak,
    stopSpeaking,
    hasSupport: true
  };
}
