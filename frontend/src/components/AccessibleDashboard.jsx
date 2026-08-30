import React from 'react';

export default function AccessibleDashboard({ children }) {
  return (
    <div className="container" style={{ padding: '2rem 1rem' }}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
        <h1 className="text-section-heading color-primary" style={{ letterSpacing: '2px', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          FIN•SIGHT
        </h1>
        <button className="btn btn-secondary" aria-label="User Profile" style={{ minHeight: '40px', padding: '8px 16px' }}>
          🔔 Profile
        </button>
      </header>
      
      <main className="flex-col gap-8">
        {children}
      </main>
    </div>
  );
}
