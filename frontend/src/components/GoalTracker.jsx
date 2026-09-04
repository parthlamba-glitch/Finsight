import React from 'react';
import { Target, TrendingUp, Sparkles } from 'lucide-react';
import { motion } from 'framer-motion';
import StatusBadge from './StatusBadge';

/**
 * GoalTracker Component
 * Financial savings goals visualization.
 *
 * NON-NEGOTIABLE RULE:
 * Strictly displays backend-provided figures without performing client-side math.
 */
export default function GoalTracker({ goals = [], onAnnounce }) {
  const goal = goals.length > 0 ? goals[0] : null;

  if (!goal) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2.5rem 1.5rem' }}>
        <Target size={36} color="var(--fs-text-muted)" style={{ marginBottom: '0.75rem' }} aria-hidden="true" />
        <h3 className="text-card-heading" style={{ color: 'var(--fs-text)', marginBottom: '0.5rem' }}>
          Savings Goals
        </h3>
        <p className="text-secondary" style={{ fontStyle: 'italic', margin: 0 }}>
          No active savings goals found. Ask FinSight Copilot to configure a goal anytime.
        </p>
      </div>
    );
  }

  const currentAmountStr = Number(goal.current_amount).toLocaleString('en-IN');
  const targetAmountStr = Number(goal.target_amount).toLocaleString('en-IN');
  const monthlyContributionStr = Number(goal.monthly_contribution).toLocaleString('en-IN');

  // Compute visual CSS ratio strictly for the progress bar rendering (clamped 0 to 100%)
  const visualFillPercent = Math.min(
    100,
    Math.max(0, Math.round((Number(goal.current_amount) / Math.max(1, Number(goal.target_amount))) * 100))
  );

  const handleAnnounce = () => {
    if (onAnnounce && goal) {
      onAnnounce(
        `Goal: ${goal.name}. ₹${currentAmountStr} currently saved toward a ₹${targetAmountStr} target. Committed monthly contribution is ₹${monthlyContributionStr}.`
      );
    }
  };

  return (
    <div className="card" style={{ position: 'relative', overflow: 'hidden' }}>
      {/* Header */}
      <div className="flex-between" style={{ marginBottom: '1.5rem', flexWrap: 'wrap', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
          <div
            style={{
              width: '40px',
              height: '40px',
              borderRadius: 'var(--fs-radius-md)',
              backgroundColor: 'var(--fs-accent-surface)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--fs-accent)',
              border: '1px solid rgba(141, 219, 146, 0.25)',
            }}
          >
            <Target size={22} aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-card-heading" style={{ color: 'var(--fs-text)', margin: 0 }}>
              {goal.name}
            </h3>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Committed Savings Goal
            </p>
          </div>
        </div>

        <StatusBadge variant="success" icon={<TrendingUp size={13} />}>
          ₹{monthlyContributionStr} / month
        </StatusBadge>
      </div>

      {/* Target & Saved Display Deck */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1.25rem',
          backgroundColor: 'var(--fs-bg)',
          borderRadius: 'var(--fs-radius-md)',
          padding: '1.25rem 1.5rem',
          marginBottom: '1.25rem',
          border: '1px solid var(--fs-border)',
        }}
      >
        <div>
          <span className="text-meta" style={{ display: 'block', textTransform: 'uppercase', marginBottom: '0.35rem', letterSpacing: '0.5px' }}>
            Current Saved
          </span>
          <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent)', fontWeight: 700 }}>
            ₹{currentAmountStr}
          </span>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span className="text-meta" style={{ display: 'block', textTransform: 'uppercase', marginBottom: '0.35rem', letterSpacing: '0.5px' }}>
            Target Amount
          </span>
          <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-text)', fontWeight: 600 }}>
            ₹{targetAmountStr}
          </span>
        </div>
      </div>

      {/* Animated Visual Progress Track */}
      <div
        role="progressbar"
        aria-valuenow={visualFillPercent}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-label={`${goal.name}: ₹${currentAmountStr} saved toward ₹${targetAmountStr} target`}
        style={{
          width: '100%',
          height: '10px',
          backgroundColor: 'var(--fs-bg)',
          borderRadius: 'var(--fs-radius-full)',
          overflow: 'hidden',
          marginBottom: '1.5rem',
          border: '1px solid var(--fs-border-subtle)',
        }}
      >
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${visualFillPercent}%` }}
          transition={{ duration: 0.6, ease: [0.16, 1, 0.3, 1] }}
          style={{
            height: '100%',
            backgroundColor: 'var(--fs-accent)',
            borderRadius: 'var(--fs-radius-full)',
          }}
        />
      </div>

      {/* Action Trigger */}
      <button
        type="button"
        className="btn btn-secondary"
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        onClick={handleAnnounce}
        aria-label={`Ask FinSight Copilot for completion projection on ${goal.name}`}
      >
        <Sparkles size={16} color="var(--fs-accent)" aria-hidden="true" />
        <span>Ask Copilot for goal timeline projection</span>
      </button>
    </div>
  );
}
