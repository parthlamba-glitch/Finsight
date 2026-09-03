import React, { useEffect, useState } from 'react';
import { animate } from 'framer-motion';

/**
 * AnimatedNumber Component
 * Smoothly interpolates from 0 to a backend-provided final numeric value.
 * Strictly respects prefers-reduced-motion (renders final value instantly).
 *
 * NOTE: This component ONLY visually formats and displays authoritative backend numbers.
 * It NEVER performs financial calculations or math.
 */
export default function AnimatedNumber({
  value,
  prefix = '',
  decimals = 0,
  duration = 0.5,
  className = '',
  style = {},
}) {
  const numericValue = typeof value === 'number' ? value : Number(value) || 0;
  const isNegative = numericValue < 0;
  const absValue = Math.abs(numericValue);

  const isReducedMotion = typeof window !== 'undefined' && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const [displayValue, setDisplayValue] = useState(() => (isReducedMotion ? absValue : 0));

  useEffect(() => {
    if (isReducedMotion) {
      return;
    }

    const controls = animate(0, absValue, {
      duration: Math.min(0.6, duration),
      ease: [0.16, 1, 0.3, 1], // Calm fintech easing
      onUpdate: (latest) => {
        setDisplayValue(latest);
      },
    });

    return () => controls.stop();
  }, [absValue, duration, isReducedMotion]);

  const valueToFormat = isReducedMotion ? absValue : displayValue;
  const formattedNumber = valueToFormat.toLocaleString('en-IN', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  const formattedDisplay = isNegative ? `−${prefix}${formattedNumber}` : `${prefix}${formattedNumber}`;

  return (
    <span className={`tabular-nums ${className}`} style={style}>
      {formattedDisplay}
    </span>
  );
}
