import React from 'react';
import { motion } from 'framer-motion';

/**
 * TrustScoreBar — horizontal trust score gauge (0–100).
 * Color gradient: red (0–30) → amber (30–60) → green (60–100).
 *
 * @param {number} score   Trust score 0–100
 * @param {string} className  Optional extra class
 */
function TrustScoreBar({ score = 0, className = '' }) {
  const clampedScore = Math.max(0, Math.min(100, score));

  const getBarColor = (s) => {
    if (s < 30) return 'var(--accent-danger)';
    if (s < 60) return 'var(--accent-warning)';
    return 'var(--accent-success)';
  };

  const getBarGradient = (s) => {
    if (s < 30) return 'var(--gradient-trust-low)';
    if (s < 60) return 'var(--gradient-trust-mid)';
    return 'var(--gradient-trust-high)';
  };

  return (
    <div className={`trust-bar-wrap ${className}`}>
      <div className="trust-bar-track">
        <motion.div
          className="trust-bar-fill"
          initial={{ width: 0 }}
          animate={{ width: `${clampedScore}%` }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          style={{
            background: getBarGradient(clampedScore),
            boxShadow: `0 0 8px ${getBarColor(clampedScore)}40`,
          }}
        />
      </div>
      <span
        className="trust-bar-label"
        style={{ color: getBarColor(clampedScore) }}
      >
        {clampedScore}
      </span>
    </div>
  );
}

export default TrustScoreBar;
