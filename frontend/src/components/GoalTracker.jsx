import React from 'react';
import { Target, TrendingUp, Sparkles } from 'lucide-react';
import StatusBadge from './StatusBadge';

/**
 * GoalTracker Component
 * Displays savings goals using authoritative backend values.
 *
 * NON-NEGOTIABLE RULE:
 * Strictly displays backend-provided values without performing frontend financial calculations.
 */
export default function GoalTracker({ goals = [], onAnnounce }) {
  const goal = goals.length > 0 ? goals[0] : null;

  if (!goal) {
    return (
      <div className="card" style={{ textAlign: 'center', padding: '2rem 1.5rem' }}>
        <Target size={32} color="var(--fs-text-muted, #71817A)" style={{ marginBottom: '0.75rem' }} aria-hidden="true" />
        <h3 className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', marginBottom: '0.5rem' }}>
          Savings Goals
        </h3>
        <p className="text-secondary" style={{ fontStyle: 'italic', margin: 0 }}>
          No active savings goals found. Ask FinSight to set a goal anytime.
        </p>
      </div>
    );
  }

  const currentAmountStr = Number(goal.current_amount).toLocaleString('en-IN');
  const targetAmountStr = Number(goal.target_amount).toLocaleString('en-IN');
  const monthlyContributionStr = Number(goal.monthly_contribution).toLocaleString('en-IN');

  // Compute visual CSS ratio clamped between 0% and 100% strictly for the visual bar width
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
    <div className="card" style={{ position: 'relative' }}>
      {/* Header */}
      <div className="flex-between" style={{ marginBottom: '1.25rem', flexWrap: 'wrap', gap: '0.5rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.6rem' }}>
          <div
            style={{
              width: '36px',
              height: '36px',
              borderRadius: 'var(--fs-radius-sm, 8px)',
              backgroundColor: 'var(--fs-accent-surface, rgba(141, 219, 146, 0.12))',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--fs-accent, #8DDB92)',
            }}
          >
            <Target size={20} aria-hidden="true" />
          </div>
          <div>
            <h3 className="text-card-heading" style={{ color: 'var(--fs-text, #F5F4EC)', margin: 0 }}>
              {goal.name}
            </h3>
            <p className="text-meta" style={{ textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              Active Savings Target
            </p>
          </div>
        </div>

        <StatusBadge variant="success" icon={<TrendingUp size={12} />}>
          ₹{monthlyContributionStr} / mo
        </StatusBadge>
      </div>

      {/* Target & Saved Amounts */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '1fr 1fr',
          gap: '1rem',
          backgroundColor: 'var(--fs-bg, #071510)',
          borderRadius: 'var(--fs-radius-md, 14px)',
          padding: '1rem 1.25rem',
          marginBottom: '1rem',
          border: '1px solid var(--fs-border-subtle, #142E25)',
        }}
      >
        <div>
          <span className="text-meta" style={{ display: 'block', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Current Saved
          </span>
          <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-accent, #8DDB92)', fontWeight: 700 }}>
            ₹{currentAmountStr}
          </span>
        </div>

        <div style={{ textAlign: 'right' }}>
          <span className="text-meta" style={{ display: 'block', textTransform: 'uppercase', marginBottom: '0.25rem' }}>
            Target Amount
          </span>
          <span className="text-section-heading tabular-nums" style={{ color: 'var(--fs-text, #F5F4EC)', fontWeight: 600 }}>
            ₹{targetAmountStr}
          </span>
        </div>
      </div>

      {/* Visual Progress Track */}
      <div
        role="progressbar"
        aria-valuenow={visualFillPercent}
        aria-valuemin="0"
        aria-valuemax="100"
        aria-label={`${goal.name}: ₹${currentAmountStr} saved toward ₹${targetAmountStr} target`}
        style={{
          width: '100%',
          height: '10px',
          backgroundColor: 'var(--fs-bg, #071510)',
          borderRadius: 'var(--fs-radius-full, 9999px)',
          overflow: 'hidden',
          marginBottom: '1.25rem',
          border: '1px solid var(--fs-border-subtle, #142E25)',
        }}
      >
        <div
          style={{
            width: `${visualFillPercent}%`,
            height: '100%',
            backgroundColor: 'var(--fs-accent, #8DDB92)',
            borderRadius: 'var(--fs-radius-full, 9999px)',
            transition: 'width var(--fs-transition-slow, 350ms)',
          }}
        />
      </div>

      {/* Action Button */}
      <button
        type="button"
        className="btn btn-secondary"
        style={{ width: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '0.5rem' }}
        onClick={handleAnnounce}
        aria-label={`Ask FinSight Copilot about ${goal.name}`}
      >
        <Sparkles size={16} color="var(--fs-accent, #8DDB92)" aria-hidden="true" />
        <span>Ask Copilot about this goal</span>
      </button>
    </div>
  );
}
