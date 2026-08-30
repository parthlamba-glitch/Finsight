import React, { useState, useEffect, useRef } from 'react';
import AccessibleDashboard from '../components/AccessibleDashboard';
import ChatPanel from '../components/ChatPanel';
import TransactionList from '../components/TransactionList';
import ScamChecker from '../components/ScamChecker';
import GoalTracker from '../components/GoalTracker';
import AuthModal from '../components/AuthModal';
import DocumentUpload from '../components/DocumentUpload';
import { useSpeech } from '../hooks/useSpeech';
import { api } from '../services/api';

export default function Dashboard() {
  const [answerText, setAnswerText] = useState('');
  const [isProcessingQuery, setIsProcessingQuery] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [dashboardStats, setDashboardStats] = useState({ balance: 0, spending: 0, goals: [] });
  const [transactions, setTransactions] = useState([]);
  
  // State for orchestrating the payment flow
  const [pendingPaymentId, setPendingPaymentId] = useState(null);
  const [awaitingVoiceConfirm, setAwaitingVoiceConfirm] = useState(false);
  const conversationIdRef = useRef(null);

  const { 
    isListening, 
    isProcessing, 
    setIsProcessing, 
    startListening, 
    stopListening, 
    speak,
    isSpeaking,
    stopSpeaking
  } = useSpeech(async (transcript) => {
    handleQuery(transcript);
  });

  // Welcome announcement & init stats
  useEffect(() => {
    const init = async () => {
      const stats = await api.getDashboardStats();
      const txs = await api.getTransactions();
      
      setDashboardStats(stats);
      setTransactions(txs);
      
      speak("Welcome to FinSight. What would you like to know?", () => {
        startListening();
      });
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const handleGlobalTap = (e) => {
      // If idle
      if (!isListening && !isSpeaking && !isProcessing && !isProcessingQuery && !isAuthOpen) {
        // Ignore taps on interactive elements
        if (e.target.closest('button, a, input, select, textarea')) return;
        
        speak("Are you trying to speak something?", () => {
          startListening();
        });
      }
    };

    document.addEventListener('click', handleGlobalTap);
    return () => document.removeEventListener('click', handleGlobalTap);
  }, [isListening, isSpeaking, isProcessing, isProcessingQuery, isAuthOpen, speak, startListening]);

  const handleQuery = async (query) => {
    setIsProcessing(true);
    setIsProcessingQuery(true);
    
    const lowerQuery = query.toLowerCase().replace(/[.,!?;]+$/g, '').trim();
    
    // 1. Intercept Payment Confirmation
    if (awaitingVoiceConfirm && /confirm|yes/i.test(lowerQuery)) {
      setAwaitingVoiceConfirm(false);
      setIsProcessing(false);
      setIsProcessingQuery(false);
      
      const authMsg = "Please authenticate to authorize this payment.";
      setAnswerText(authMsg);
      speak(authMsg, () => {
        setIsAuthOpen(true);
      });
      return;
    }

    try {
      // Reset pending state if they ask something else to the backend AI
      setAwaitingVoiceConfirm(false);
      setPendingPaymentId(null);

      const response = await api.askFinsight(query, conversationIdRef.current);
      
      if (response.conversation_id) {
        conversationIdRef.current = response.conversation_id;
      }
      
      setAnswerText(response.answer_text);
      
      speak(response.answer_text, () => {
        if (response.requires_confirmation) {
          setPendingPaymentId(response.pending_payment_id);
          setAwaitingVoiceConfirm(true);
          startListening();
        } else {
          startListening();
        }
      });
      
    } catch (error) {
      console.error(error);
      const errorMsg = "I'm sorry, I had trouble processing that request.";
      setAnswerText(errorMsg);
      speak(errorMsg, () => {
        startListening();
      });
    } finally {
      setIsProcessing(false);
      setIsProcessingQuery(false);
    }
  };

  const handleAuthenticate = async () => {
    setIsAuthOpen(false);
    try {
      if (!pendingPaymentId) throw new Error("No pending payment ID.");
      
      const payment = await api.executePayment(pendingPaymentId);
      const stats = await api.getDashboardStats();
      setDashboardStats(stats);
      setPendingPaymentId(null);
      setAwaitingVoiceConfirm(false);
      
      const successMsg = `Payment successful. ₹${payment.amount} was sent to ${payment.recipient_name}. Your new balance is ₹${payment.new_balance.toLocaleString('en-IN')}.`;
      setAnswerText(successMsg);
      speak(successMsg, () => {
        startListening();
      });
    } catch (err) {
      const errMsg = "Payment failed. " + err.message;
      setAnswerText(errMsg);
      speak(errMsg, () => startListening());
    }
  };

  const handleAuthCancel = () => {
    setIsAuthOpen(false);
    setPendingPaymentId(null);
    setAwaitingVoiceConfirm(false);
    const cancelMsg = "Payment cancelled.";
    setAnswerText(cancelMsg);
    speak(cancelMsg, () => startListening());
  };

  const handleReplay = () => {
    if (answerText) speak(answerText);
  };
  
  const handleAnnounce = (text) => {
    speak(text);
  };

  const handleRefreshData = async () => {
    try {
      const newTxs = await api.getTransactions();
      const newStats = await api.getDashboardStats();
      setTransactions(newTxs);
      setDashboardStats(newStats);
    } catch (err) {
      console.error("Failed to refresh data", err);
    }
  };

  const handleSyncBank = async () => {
    try {
      const res = await api.syncBank();
      await handleRefreshData();
      speak(`Bank sync complete. Found ${res.imported_count} new transactions and skipped ${res.duplicate_count} duplicates.`);
    } catch (err) {
      speak("Failed to sync bank feed.");
    }
  };

  return (
    <AccessibleDashboard>
      
      <AuthModal 
        isOpen={isAuthOpen} 
        onAuthenticate={handleAuthenticate} 
        onCancel={handleAuthCancel} 
      />

      <section aria-labelledby="overview-heading">
        <h2 id="overview-heading" className="text-section-heading" style={{ color: 'var(--color-text-muted)', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '1px' }}>
          Overview
        </h2>
        <p className="text-page-heading" style={{ marginTop: '0.5rem' }}>Good evening</p>
        <p className="text-secondary" style={{ fontSize: '1.1rem' }}>Here's what's happening with your money.</p>
      </section>

      {/* 1. ACCESS Pillar (Always visible hero) */}
      <ChatPanel 
        onQuerySubmit={handleQuery} 
        isProcessing={isProcessing || isProcessingQuery} 
        answerText={answerText}
        onReplay={handleReplay}
        isSpeaking={isSpeaking}
        stopSpeaking={stopSpeaking}
        isListening={isListening}
        onStartListening={startListening}
        onStopListening={stopListening}
      />
      
      {/* 2. FINANCIAL PULSE */}
      <section aria-labelledby="pulse-heading">
        <h2 id="pulse-heading" className="text-section-heading" style={{ color: 'var(--color-text-muted)', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '1rem' }}>
          Financial Pulse
        </h2>
        <div className="flex-col gap-4">
          <div className="card">
            <h3 className="text-secondary" style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem' }}>Balance</h3>
            <p className="text-page-heading">₹{dashboardStats.balance.toLocaleString('en-IN')}</p>
            <p className="text-secondary">Available</p>
          </div>
          <div className="card">
            <h3 className="text-secondary" style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem' }}>Spending</h3>
            <p className="text-page-heading">₹{dashboardStats.spending.toLocaleString('en-IN')}</p>
            <p className="text-secondary">This month</p>
          </div>
        </div>
      </section>

      {/* 3. PROTECT Pillar */}
      <section aria-label="Protection">
        <ScamChecker onAnnounce={handleAnnounce} />
      </section>

      {/* 4. DECIDE Pillar (Goals) */}
      <section aria-label="Goals">
        <GoalTracker goals={dashboardStats.goals || []} onAnnounce={handleAnnounce} />
      </section>
      
      {/* 5. UPLOAD DOCUMENTS */}
      <section aria-label="Upload Documents">
        <DocumentUpload onAnnounce={handleAnnounce} onRefresh={handleRefreshData} />
      </section>
      
      {/* 6. RECENT ACTIVITY (Transactions) */}
      <section aria-label="Recent Activity">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
          <h2 id="recent-activity-heading" className="text-section-heading" style={{ color: 'var(--color-text-muted)', fontSize: '1rem', textTransform: 'uppercase', letterSpacing: '1px', margin: 0 }}>
            Recent Activity
          </h2>
          <button 
            className="btn btn-secondary" 
            onClick={handleSyncBank}
            style={{ padding: '8px 16px', fontSize: '0.875rem', borderRadius: '20px' }}
            aria-label="Refresh Bank Feed"
          >
            🔄 Sync Bank
          </button>
        </div>
        <TransactionList transactions={transactions} />
      </section>

    </AccessibleDashboard>
  );
}
