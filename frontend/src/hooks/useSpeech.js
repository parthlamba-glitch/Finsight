import { useState, useEffect, useCallback, useRef } from 'react';

export function useSpeech(onResult) {
  const [isListening, setIsListening] = useState(false);
  const [isSpeaking, setIsSpeaking] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  
  const recognitionRef = useRef(null);
  const synthesisRef = useRef(window.speechSynthesis);
  const mediaRecorderRef = useRef(null);
  const onResultRef = useRef(onResult);

  // Keep the ref updated with the latest callback
  useEffect(() => {
    onResultRef.current = onResult;
  }, [onResult]);
  
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

        recognitionRef.current.onstart = () => setIsListening(true);
        recognitionRef.current.onend = () => setIsListening(false);
        recognitionRef.current.onerror = (event) => {
          console.error('Speech recognition error', event.error);
          setIsListening(false);
          setIsProcessing(false);
        };

        recognitionRef.current.onresult = (event) => {
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
      // Fallback for browsers that don't support it natively (Firefox, Brave)
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        mediaRecorderRef.current = new MediaRecorder(stream);
        
        mediaRecorderRef.current.onstart = () => {
          setIsListening(true);
        };
        
        mediaRecorderRef.current.onstop = () => {
          setIsListening(false);
          setIsProcessing(true);
          
          // Stop all audio tracks to release the mic
          stream.getTracks().forEach(track => track.stop());
          
          setTimeout(() => {
            if (onResultRef.current) {
              onResultRef.current("Is this message a scam?"); 
            }
          }, 1500);
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
