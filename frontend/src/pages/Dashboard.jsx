import React, { useState, useEffect, useRef, useCallback } from 'react';
import { RefreshCw, TrendingUp } from 'lucide-react';
import AccessibleDashboard from '../components/AccessibleDashboard';
import ChatPanel from '../components/ChatPanel';
import TransactionList from '../components/TransactionList';
import ScamChecker from '../components/ScamChecker';
import GoalTracker from '../components/GoalTracker';
import AuthModal from '../components/AuthModal';
import DocumentUpload from '../components/DocumentUpload';
import Skeleton from '../components/Skeleton';
import StatusBadge from '../components/StatusBadge';
import AnimatedNumber from '../components/AnimatedNumber';
import { useSpeech } from '../hooks/useSpeech';
import { api } from '../services/api';
import { useAuth } from '../hooks/useAuth';

function getTimeOfDayGreeting() {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default function Dashboard() {
  const { user } = useAuth();

  const [answerText, setAnswerText] = useState('');
  const [isProcessingQuery, setIsProcessingQuery] = useState(false);
  const [isAuthOpen, setIsAuthOpen] = useState(false);
  const [isExecutingPayment, setIsExecutingPayment] = useState(false);
  const [isSyncingBank, setIsSyncingBank] = useState(false);
  const [isLoadingData, setIsLoadingData] = useState(true);

  const [dashboardStats, setDashboardStats] = useState({
    balance: null,
    spending: null,
    income: null,
    surplus: null,
    savings: null,
    upcomingBills: null,
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
    } finally {
      setIsLoadingData(false);
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
  } = useSpeech(
    async (transcript) => {
      handleQuery(transcript);
    },
    async (audioBlob, ext, recDuration) => {
      handleVoiceAudio(audioBlob, ext, recDuration);
    }
  );

  // Initial dashboard load
  useEffect(() => {
    const init = async () => {
      await refreshFinancialData();
      const firstName = user?.full_name ? `, ${user.full_name.split(' ')[0]}` : '';
      speak(`Welcome to FinSight${firstName}. What would you like to know today?`, () => {
        startListening();
      });
    };
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [refreshFinancialData]);

  // Global tap-to-speak handler for accessibility
  useEffect(() => {
    const handleGlobalTap = (e) => {
      if (!isListening && !isSpeaking && !isProcessing && !isProcessingQuery && !isAuthOpen) {
        if (e.target.closest('button, a, input, select, textarea, [role="tab"], [role="button"], [role="dialog"]')) return;
        speak('Are you trying to say something?', () => {
          startListening();
        });
      }
    };

    document.addEventListener('click', handleGlobalTap);
    return () => document.removeEventListener('click', handleGlobalTap);
  }, [isListening, isSpeaking, isProcessing, isProcessingQuery, isAuthOpen, speak, startListening]);

  /**
   * Common Response Processor for Copilot Answers
   */
  const processCopilotResponse = async (response) => {
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
  };

  /**
   * Direct Voice Audio Pipeline Handler (Unified Single Network Trip)
   */
  const handleVoiceAudio = async (audioBlob, ext = 'webm', recordingDurationMs = 0) => {
    setIsProcessing(true);
    setIsProcessingQuery(true);
    const t_upload_start = performance.now();

    try {
      const response = await api.askVoice(
        audioBlob,
        `recording.${ext}`,
        conversationIdRef.current,
        stagedPayment?.confirmation_token || null,
        'en'
      );
      const networkMs = performance.now() - t_upload_start;
      const totalVoiceLatency = recordingDurationMs + networkMs;

      console.log(`[VOICE PIPELINE TIMING BREAKDOWN]
  1. Frontend Recording Duration: ${recordingDurationMs.toFixed(1)}ms
  2. Audio Upload + Voice Pipeline Duration: ${networkMs.toFixed(1)}ms
  3. STT Duration: ${response.timing_ms?.stt_ms ?? 'N/A'}ms
  4. /ask Backend Request Duration: ${response.timing_ms?.pipeline_total_ms ?? 'N/A'}ms
  5. Intent Routing Duration: ${response.timing_ms?.intent_routing_ms ?? 'N/A'}ms
  6. Financial Tool Execution Duration: ${response.timing_ms?.financial_tool_execution_ms ?? 'N/A'}ms
  7. Final LLM Generation Duration: ${response.timing_ms?.explainer_ms ?? 'N/A'}ms
  8. Total Voice-to-Response Latency: ${totalVoiceLatency.toFixed(1)}ms`);

      if (response.transcript) {
        console.log(`[VOICE TRANSCRIPT]: "${response.transcript}"`);
      }

      await processCopilotResponse(response);
    } catch (err) {
      console.error('Unified voice query error, falling back to text ask:', err);
      handleQuery("What's my balance?");
    } finally {
      setIsProcessing(false);
      setIsProcessingQuery(false);
    }
  };

  /**
   * Primary Conversational Query Handler (Text or Browser SpeechRecognition)
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

    const t_ask_start = performance.now();

    try {
      // Dispatch query to backend /ask preserving multi-turn conversation session
      const response = await api.askFinsight(
        cleanQuery,
        conversationIdRef.current,
        stagedPayment?.confirmation_token || null,
        true
      );
      const askDurationMs = performance.now() - t_ask_start;
      console.log(`[ASK TIMING] 4. /ask request duration: ${askDurationMs.toFixed(1)}ms (Routing: ${response.timing_ms?.intent_routing_ms}ms, Tool: ${response.timing_ms?.financial_tool_execution_ms}ms, Explainer: ${response.timing_ms?.explainer_ms}ms, Total: ${response.timing_ms?.pipeline_total_ms}ms)`);

      await processCopilotResponse(response);
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

      const result = await api.executePayment(pendingPaymentId);
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
    setIsSyncingBank(true);
    try {
      const res = await api.syncBank();
      await refreshFinancialData();
      const msg = `Bank sync complete. Recorded ${res.imported_count} new transactions and skipped ${res.duplicate_count} duplicates.`;
      speak(msg);
    } catch (err) {
      speak('Failed to sync bank feed: ' + err.message);
    } finally {
      setIsSyncingBank(false);
    }
  };

  const greeting = getTimeOfDayGreeting();
  const userName = user?.full_name ? `, ${user.full_name}` : '';

  return (
    <AccessibleDashboard onAnnounce={handleAnnounce}>
      {/* 0. Staged Payment Confirmation Modal */}
      <AuthModal
        isOpen={isAuthOpen}
        paymentDetails={stagedPayment}
        onConfirm={handleModalConfirm}
        onCancel={handleModalCancel}
        isExecuting={isExecutingPayment}
      />

      {/* 1. HERO FINANCIAL BALANCE (VISUAL ANCHOR) */}
      <section aria-labelledby="hero-balance-heading">
        <div
          className="card card-hero"
          style={{
            padding: '2.5rem 2rem',
            position: 'relative',
            overflow: 'hidden',
          }}
        >
          <div className="flex-between" style={{ flexWrap: 'wrap', gap: '0.75rem', marginBottom: '0.75rem' }}>
            <span
              id="hero-balance-heading"
              className="text-meta"
              style={{
                textTransform: 'uppercase',
                letterSpacing: '1px',
                fontWeight: 700,
                color: 'var(--fs-accent, #8DDB92)',
              }}
            >
              Authoritative Balance · Primary Account
            </span>

            {dashboardStats.surplus !== null && Number(dashboardStats.surplus) > 0 && (
              <StatusBadge variant="success" icon={<TrendingUp size={12} />}>
                +₹{Number(dashboardStats.surplus).toLocaleString('en-IN')} Monthly Surplus
              </StatusBadge>
            )}
          </div>

          {isLoadingData ? (
            <Skeleton height="56px" width="320px" borderRadius="12px" ariaLabel="Loading authoritative balance..." />
          ) : (
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '0.5rem', margin: '0.5rem 0 1rem' }}>
              <AnimatedNumber
                value={dashboardStats.balance || 0}
                prefix="₹"
                decimals={2}
                className="text-hero"
                style={{
                  color: 'var(--fs-text, #F5F4EC)',
                  fontSize: 'clamp(2.5rem, 6vw, 3.5rem)',
                  fontWeight: 700,
                }}
              />
            </div>
          )}

          <p className="text-secondary" style={{ fontSize: '1.05rem', margin: 0 }}>
            {greeting}{userName}. Here is your live financial pulse.
          </p>
        </div>
      </section>

      {/* 2. COPILOT HERO CENTERPIECE (ACCESS PILLAR) */}
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

      {/* 3. FINANCIAL PULSE METRICS ROW */}
      <section aria-labelledby="pulse-heading">
        <div className="flex-between" style={{ marginBottom: '1rem' }}>
          <h2
            id="pulse-heading"
            className="text-meta"
            style={{
              color: 'var(--fs-text-muted, #71817A)',
              textTransform: 'uppercase',
              letterSpacing: '1px',
              fontWeight: 700,
            }}
          >
            Financial Pulse Metrics
          </h2>
          <span className="text-meta">Authoritative Engine Data</span>
        </div>

        <div className="metrics-grid">
          {/* Card 1: Monthly Spending */}
          <div className="card">
            <span className="text-meta" style={{ textTransform: 'uppercase', display: 'block', marginBottom: '0.35rem' }}>
              Monthly Spending
            </span>
            {isLoadingData ? (
              <Skeleton height="36px" width="160px" />
            ) : (
              <p className="text-page-heading tabular-nums" style={{ color: 'var(--fs-text, #F5F4EC)' }}>
                ₹{Number(dashboardStats.spending || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
            )}
            <p className="text-secondary" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Current calendar month
            </p>
          </div>

          {/* Card 2: Monthly Income */}
          <div className="card">
            <span className="text-meta" style={{ textTransform: 'uppercase', display: 'block', marginBottom: '0.35rem' }}>
              Monthly Income
            </span>
            {isLoadingData ? (
              <Skeleton height="36px" width="160px" />
            ) : (
              <p className="text-page-heading tabular-nums" style={{ color: 'var(--fs-accent, #8DDB92)' }}>
                ₹{Number(dashboardStats.income || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
            )}
            <p className="text-secondary" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Active accounts baseline
            </p>
          </div>

          {/* Card 3: Upcoming Unpaid Bills */}
          <div className={`card ${Number(dashboardStats.upcomingBills || 0) > 0 ? 'card-warning' : ''}`}>
            <div className="flex-between" style={{ marginBottom: '0.35rem' }}>
              <span className="text-meta" style={{ textTransform: 'uppercase' }}>
                Upcoming Commitments
              </span>
              {Number(dashboardStats.upcomingBills || 0) > 0 && (
                <StatusBadge variant="warning" showDot={false}>
                  Due Soon
                </StatusBadge>
              )}
            </div>
            {isLoadingData ? (
              <Skeleton height="36px" width="160px" />
            ) : (
              <p
                className="text-page-heading tabular-nums"
                style={{
                  color: Number(dashboardStats.upcomingBills || 0) > 0 ? 'var(--fs-warning-bright, #F5CF80)' : 'var(--fs-text, #F5F4EC)',
                }}
              >
                ₹{Number(dashboardStats.upcomingBills || 0).toLocaleString('en-IN', { minimumFractionDigits: 2 })}
              </p>
            )}
            <p className="text-secondary" style={{ fontSize: '0.85rem', marginTop: '0.25rem' }}>
              Unpaid bills due in 30 days
            </p>
          </div>
        </div>
      </section>

      {/* 4. FINANCIAL GOALS (DECIDE PILLAR) */}
      <section aria-label="Savings Goals">
        <GoalTracker goals={dashboardStats.goals || []} onAnnounce={handleAnnounce} />
      </section>

      {/* 5. RECENT TRANSACTION ACTIVITY */}
      <section aria-labelledby="recent-activity-heading">
        <div
          style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            marginBottom: '1rem',
            flexWrap: 'wrap',
            gap: '0.75rem',
          }}
        >
          <div>
            <h2
              id="recent-activity-heading"
              className="text-meta"
              style={{
                color: 'var(--fs-text-muted, #71817A)',
                textTransform: 'uppercase',
                letterSpacing: '1px',
                fontWeight: 700,
                margin: 0,
              }}
            >
              Recent Ledger Activity
            </h2>
          </div>

          <button
            type="button"
            className="btn btn-secondary"
            onClick={handleSyncBank}
            disabled={isSyncingBank}
            style={{
              padding: '6px 14px',
              fontSize: '0.85rem',
              minHeight: '38px',
              borderRadius: 'var(--fs-radius-full, 9999px)',
            }}
            aria-label="Synchronize live bank feed"
          >
            <RefreshCw size={14} className={isSyncingBank ? 'spin' : ''} aria-hidden="true" />
            <span>{isSyncingBank ? 'Syncing...' : 'Sync Bank Feed'}</span>
          </button>
        </div>

        {isLoadingData ? (
          <div className="card flex-col gap-3">
            <Skeleton height="32px" width="100%" />
            <Skeleton height="32px" width="100%" />
            <Skeleton height="32px" width="100%" />
          </div>
        ) : (
          <TransactionList transactions={transactions} />
        )}
      </section>

      {/* 6. SECURITY & SCAM SHIELD (PROTECT PILLAR) */}
      <section aria-label="Security and Fraud Shield">
        <ScamChecker onAnnounce={handleAnnounce} />
      </section>

      {/* 7. BANK STATEMENT INGESTION (DOCUMENTS) */}
      <section aria-label="Document Ingestion and Scanner">
        <DocumentUpload onAnnounce={handleAnnounce} onRefresh={refreshFinancialData} />
      </section>
    </AccessibleDashboard>
  );
}
