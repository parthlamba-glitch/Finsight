import React from 'react';

/**
 * StatusBadge Component
 * Semantic badge for risk, verification, categories, and account status.
 *
 * Variants: 'neutral' | 'success' | 'warning' | 'danger'
 */
export default function StatusBadge({
  variant = 'neutral',
  children,
  icon = null,
  showDot = true,
  className = '',
  style = {},
}) {
  const variantClass = `chip-${variant}`;

  return (
    <span
      className={`chip ${variantClass} ${className}`}
      style={style}
    >
      {showDot && !icon && (
        <span
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            backgroundColor: 'currentColor',
            display: 'inline-block',
          }}
          aria-hidden="true"
        />
      )}
      {icon && <span aria-hidden="true" style={{ display: 'inline-flex' }}>{icon}</span>}
      <span>{children}</span>
    </span>
  );
}
