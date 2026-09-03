import React from 'react';

/**
 * Accessible Skeleton Component
 * Provides subtle, accessible shimmer placeholders for async surfaces.
 * Respects prefers-reduced-motion.
 */
export default function Skeleton({
  width = '100%',
  height = '20px',
  borderRadius = 'var(--fs-radius-sm, 8px)',
  className = '',
  style = {},
  ariaLabel = 'Loading content...',
}) {
  return (
    <div
      className={`skeleton ${className}`}
      style={{
        width,
        height,
        borderRadius,
        ...style,
      }}
      role="status"
      aria-label={ariaLabel}
    />
  );
}
