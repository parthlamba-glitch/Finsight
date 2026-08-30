import React, { useState, useEffect, useRef, useCallback } from 'react';
import AccessibleDashboard from '../components/AccessibleDashboard';
import ChatPanel from '../components/ChatPanel';
import TransactionList from '../components/TransactionList';
import ScamChecker from '../components/ScamChecker';
import GoalTracker from '../components/GoalTracker';
import AuthModal from '../components/AuthModal';
import DocumentUpload from '../components/DocumentUpload';
import { useSpeech } from '../hooks/useSpeech';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';

export default function Dashboard() {
  const { user } = useAuth();

  const [answerText, setAnswerText] = useState('');
  const [isProcessingQuery, setIsProcessingQuery] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isExecutingPayment, setIsExecutingPayment] = useState(false);

  const [dashboardStats, setDashboardStats] = useState({
    balance: 0,
    spending: 0,
    income: 0,
    surplus: 0,
    savings: 0,
    upcomingBills: 0,
    goals: [],
  });
  const [transactions, setTransactions] = useState([]);

  // Staged payment state
  const [stagedPayment, setStagedPayment] = useState(null);
  const [awaitingConfirmation, setAwaitingConfirmation] = useState(false);

  // Multi-turn conversation tracker
  const conversationIdRef = useRef(null);

  const handleAnnounce = useCallback((text) => {
    speak(text);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const refreshFinancialData = useCallback(async () => {
    try {
      const stats = await api.getDashboardStats();
      const txs = await api.getTransactions('this_month');
      setDashboardStats(stats);
      setTransactions(txs);
    } catch (err) {
      console.error('Failed to load dashboard data:', err.message);
    }
  }, []);

  const {
    isListening,
    isProcessing,
    setIsProcessing,
    startListening,
    stopListening,
    speak,
    isSpeaking,
    stopSpeaking,
  } = useSpeech(async (transcript) => {
    handleQuery(transcript);
  });

  // Initial dashboard load
  useEffect(() => {
    const init = async () => {
      await refreshFinancialData();
      const greetingName = user?.full_name ? `, ${user.full_name.split(' ')[0]}` : '';
      speak(`Welcome to FinSight${greetingName}. What would you like to know today?`, () => {
        startListening();
      });
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshFinancialData]);

  // Global tap to speak handler
  useEffect(() => {
    const handleGlobalTap = (e) => {
      if (!isListening && !isSpeaking && !isProcessing && !isProcessingQuery && !isAuthOpen) {
        if (e.target.closest('button, a, input, select, textarea, [role="tab"], [role="button"]')) return;
        speak('Are you trying to say something?', () => {
          startListening();
        });
      }
    };

    document.addEventListener('click', handleGlobalTap);
    return () => document.removeEventListener('click', handleGlobalTap);
  }, [isListening, isSpeaking, isProcessing, isProcessingQuery, isAuthOpen, speak, startListening]);

  /**
   * Primary Conversational Query Handler
   */
  const handleQuery = async (query) => {
    setIsProcessing(true);
    setIsProcessingQuery(true);

    const cleanQuery = query.trim();
    const lowerQuery = cleanQuery.toLowerCase().replace(/[.,!?;]+$/g, '');

    // 1. Intercept explicit Voice Confirmation for staged payment
    if (awaitingConfirmation && stagedPayment && /^(yes|confirm|authorize|pay|proceed|send it|yes please)$/i.test(lowerQuery)) {
      setAwaitingConfirmation(false);
      setIsProcessing(false);
      setIsProcessingQuery(false);

      // Trigger payment execution directly
      await executeConfirmedPayment(stagedPayment.pending_payment_id);
      return;
    }

    // 2. Intercept explicit Cancellation
    if (awaitingConfirmation && /^(no|cancel|stop|abort|don't send|nevermind)$/i.test(lowerQuery)) {
      setAwaitingConfirmation(false);
      setStagedPayment(null);
      setIsAuthOpen(false);
      setIsProcessing(false);
      setIsProcessingQuery(false);
      const cancelMsg = 'Payment cancelled.';
      setAnswerText(cancelMsg);
      speak(cancelMsg, () => startListening());
      return;
    }

    try {
      // Dispatch query to backend /ask preserving multi-turn conversation session
      const response = await api.askFinsight(
        cleanQuery,
        conversationIdRef.current,
        stagedPayment?.confirmation_token || null,
        true
      );

      // Preserve multi-turn conversation_id
      if (response.conversation_id) {
        conversationIdRef.current = response.conversation_id;
      }

      setAnswerText(response.answer_text);

      const facts = response.structured_facts || response.structured_data || {};

      // Handle Staged Payment Preview
      if (response.requires_confirmation || response.intent === 'payment_preview' || facts.pending_payment_id) {
        const paymentInfo = {
          pending_payment_id: response.pending_payment_id || facts.pending_payment_id,
          confirmation_token: response.confirmation_token || facts.confirmation_token || String(facts.pending_payment_id),
          amount: facts.amount,
          recipient_name: facts.recipient_name,
          current_balance: facts.current_balance,
          balance_after: facts.balance_after,
          upcoming_bills: facts.upcoming_bills,
          risk_level: facts.risk_level || 'low',
          fraud_warning: Boolean(facts.fraud_warning),
          risk_reasons: facts.risk_reasons || [],
        };

        setStagedPayment(paymentInfo);
        setAwaitingConfirmation(true);
        setIsAuthOpen(true);

        speak(response.answer_text, () => {
          startListening();
        });
      } else {
        // Normal conversational response
        setAwaitingConfirmation(false);
        setStagedPayment(null);
        setIsAuthOpen(false);

        // If intent modified data (e.g. payment execute or bank sync), refresh
        if (response.intent === 'payment_execute' || response.intent === 'sync_bank') {
          await refreshFinancialData();
        }

        speak(response.answer_text, () => {
          startListening();
        });
      }
    } catch (error) {
      console.error('Ask error:', error);
      const errorMsg = "I'm sorry, I had trouble connecting to the financial engine. Please try again.";
      setAnswerText(errorMsg);
      speak(errorMsg, () => {
        startListening();
      });
    } finally {
      setIsProcessing(false);
      setIsProcessingQuery(false);
    }
  };

  /**
   * Executes Authoritative Pending Payment via Backend
   */
  const executeConfirmedPayment = async (pendingPaymentId) => {
    setIsExecutingPayment(true);
    setIsAuthOpen(false);

    try {
      if (!pendingPaymentId) {
        throw new Error('No pending payment identifier found.');
      }

      // Call authoritative backend execution endpoint
      const result = await api.executePayment(pendingPaymentId);

      // Refresh balances and transactions from authoritative backend
      await refreshFinancialData();

      setStagedPayment(null);
      setAwaitingConfirmation(false);

      const formattedNewBalance = Number(result.new_balance).toLocaleString('en-IN');
      const successMsg = `Payment successful! ₹${Number(result.amount).toLocaleString('en-IN')} was sent to ${result.recipient_name}. Your new balance is ₹${formattedNewBalance}.`;

      setAnswerText(successMsg);
      speak(successMsg, () => {
        startListening();
      });
    } catch (err) {
      const failMsg = `Payment failed: ${err.message}`;
      setAnswerText(failMsg);
      speak(failMsg, () => {
        startListening();
      });
    } finally {
      setIsExecutingPayment(false);
    }
  };

  const handleModalConfirm = () => {
    if (stagedPayment?.pending_payment_id) {
      executeConfirmedPayment(stagedPayment.pending_payment_id);
    }
  };

  const handleModalCancel = () => {
    setIsAuthOpen(false);
    setStagedPayment(null);
    setAwaitingConfirmation(false);
    const cancelMsg = 'Payment cancelled.';
    setAnswerText(cancelMsg);
    speak(cancelMsg, () => startListening());
  };

  const handleReplay = () => {
    if (answerText) speak(answerText);
  };

  const handleSyncBank = async () => {
    try {
      const res = await api.syncBank();
      await refreshFinancialData();
      const msg = `Bank sync complete. Found ${res.imported_count} new transactions and skipped ${res.duplicate_count} duplicates.`;
      speak(msg);
    } catch (err) {
      speak('Failed to sync bank feed: ' + err.message);
    }
  };

  return (
    <AccessibleDashboard onAnnounce={handleAnnounce}>
      <AuthModal
        isOpen={isAuthOpen}
        paymentDetails={stagedPayment}
        onConfirm={handleModalConfirm}
        onCancel={handleModalCancel}
        isExecuting={isExecutingPayment}
      />

      <section aria-labelledby="overview-heading">
        <h2
          id="overview-heading"
          className="text-section-heading"
          style={{
            color: 'var(--color-text-muted)',
            fontSize: '1rem',
            textTransform: 'uppercase',
            letterSpacing: '1px',
          }}
        >
          Overview
        </h2>
        <p className="text-page-heading" style={{ marginTop: '0.5rem' }}>
          Good day{user?.full_name ? `, ${user.full_name}` : ''}
        </p>
        <p className="text-secondary" style={{ fontSize: '1.1rem' }}>
          Here is your authoritative financial status.
        </p>
      </section>

      {/* 1. ACCESS Pillar (Conversational Hero) */}
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
        <h2
          id="pulse-heading"
          className="text-section-heading"
          style={{
            color: 'var(--color-text-muted)',
            fontSize: '1rem',
            textTransform: 'uppercase',
            letterSpacing: '1px',
            marginBottom: '1rem',
          }}
        >
          Financial Pulse
        </h2>
        <div className="flex-col gap-4">
          <div className="card">
            <h3
              className="text-secondary"
              style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem' }}
            >
              Authoritative Balance
            </h3>
            <p className="text-page-heading">₹{Number(dashboardStats.balance || 0).toLocaleString('en-IN')}</p>
            <p className="text-secondary">Available in primary account</p>
          </div>

          <div className="card">
            <h3
              className="text-secondary"
              style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem' }}
            >
              Spending
            </h3>
            <p className="text-page-heading">₹{Number(dashboardStats.spending || 0).toLocaleString('en-IN')}</p>
            <p className="text-secondary">This month</p>
          </div>

          {dashboardStats.upcomingBills > 0 && (
            <div className="card">
              <h3
                className="text-secondary"
                style={{ textTransform: 'uppercase', letterSpacing: '1px', marginBottom: '0.5rem' }}
              >
                Upcoming Bills (30 Days)
              </h3>
              <p className="text-page-heading" style={{ color: 'var(--color-warning)' }}>
                ₹{Number(dashboardStats.upcomingBills || 0).toLocaleString('en-IN')}
              </p>
              <p className="text-secondary">Due within 30 days</p>
            </div>
          )}
        </div>
      </section>

      {/* 3. PROTECT Pillar */}
      <section aria-label="Protection and Scam Checking">
        <ScamChecker onAnnounce={handleAnnounce} />
      </section>

      {/* 4. DECIDE Pillar (Goals) */}
      <section aria-label="Financial Goals">
        <GoalTracker goals={dashboardStats.goals || []} onAnnounce={handleAnnounce} />
      </section>

      {/* 5. UPLOAD DOCUMENTS */}
      <section aria-label="Upload Documents">
        <DocumentUpload onAnnounce={handleAnnounce} onRefresh={refreshFinancialData} />
      </section>

      {/* 6. RECENT ACTIVITY */}
      <section aria-label="Recent Activity">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1.5rem',
            flexWrap: 'wrap',
            gap: '0.5rem',
          }}
        >
          <h2
            id="recent-activity-heading"
            className="text-section-heading"
            style={{
              color: 'var(--color-text-muted)',
              fontSize: '1rem',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              margin: 0,
            }}
          >
            Recent Activity
          </h2>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSyncBank}
            style={{ padding: '8px 16px', fontSize: '0.875rem', borderRadius: '20px' }}
            aria-label="Synchronize Bank Feed"
          >
            🔄 Sync Bank Feed
          </button>
        </div>
        <TransactionList transactions={transactions} />
      </section>
    </AccessibleDashboard>
  );
}
