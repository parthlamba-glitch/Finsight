import React from 'react';

export default function GoalTracker({ goals = [], onAnnounce }) {
  const goal = goals.length > 0 ? goals[0] : null;

  const handleAnnounce = () => {
    if (onAnnounce && goal) {
      const percentage = Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100));
      const remaining = goal.target_amount - goal.current_amount;
      onAnnounce(`${goal.name} is ${percentage} percent complete. ₹${goal.current_amount.toLocaleString('en-IN')} saved toward a ₹${goal.target_amount.toLocaleString('en-IN')} target. ₹${remaining.toLocaleString('en-IN')} remaining.`);
    }
  };

  if (!goal) return null;

  const percentage = Math.min(100, Math.round((goal.current_amount / goal.target_amount) * 100));
  const remaining = goal.target_amount - goal.current_amount;

  return (
    <div className="card">
      <h3 className="text-card-heading" style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', marginBottom: '1rem' }}>
        🎯 {goal.name}
      </h3>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
        <span className="text-body" style={{ fontWeight: 600 }}>₹{goal.current_amount.toLocaleString('en-IN')} saved</span>
        <span className="text-secondary">₹{goal.target_amount.toLocaleString('en-IN')} target</span>
      </div>
      
      <div 
        style={{ width: '100%', height: '12px', backgroundColor: 'var(--color-bg)', borderRadius: '6px', overflow: 'hidden', marginBottom: '0.5rem' }}
        role="progressbar" 
        aria-valuenow={percentage} 
        aria-valuemin="0" 
        aria-valuemax="100" 
        aria-label={`${goal.name} is ${percentage} percent complete. ${goal.current_amount} rupees saved toward a ${goal.target_amount} rupee target.`}
      >
        <div style={{ width: `${percentage}%`, height: '100%', backgroundColor: 'var(--color-primary)' }} />
      </div>
      
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
        <span className="text-secondary">{percentage}%</span>
        <span className="text-body color-warning" style={{ fontSize: '0.9rem' }}>₹{remaining.toLocaleString('en-IN')} remaining</span>
      </div>
      
      <button className="btn btn-secondary" style={{ width: '100%' }} onClick={handleAnnounce}>
        Ask FinSight about this goal
      </button>
    </div>
  );
}
