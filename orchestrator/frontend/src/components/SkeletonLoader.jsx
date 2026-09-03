import React from 'react';

/**
 * SkeletonLoader — shimmer-animated loading placeholders.
 *
 * @param {'stat'|'card'|'timeline'|'text'} variant
 * @param {number} count   Number of skeleton items to render (default 1)
 */
function SkeletonLoader({ variant = 'card', count = 1 }) {
  const items = Array.from({ length: count }, (_, i) => i);

  if (variant === 'stat') {
    return (
      <div className="summary-grid">
        {items.map((i) => (
          <div key={i} className="summary-card glass-surface skeleton-stat-card">
            <div className="skeleton skeleton-text" style={{ width: '40%', height: '12px' }} />
            <div className="skeleton skeleton-text" style={{ width: '60%', height: '28px', marginTop: '10px' }} />
            <div className="skeleton skeleton-text" style={{ width: '80%', height: '10px', marginTop: '8px' }} />
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'card') {
    return (
      <div className="card-grid two-col">
        {items.map((i) => (
          <div key={i} className="entity-card glass-surface">
            <div className="skeleton skeleton-text" style={{ width: '65%', height: '16px' }} />
            <div className="skeleton skeleton-text" style={{ width: '40%', height: '12px', marginTop: '8px' }} />
            <div className="skeleton skeleton-text" style={{ width: '90%', height: '12px', marginTop: '8px' }} />
            <div className="skeleton skeleton-text" style={{ width: '50%', height: '12px', marginTop: '8px' }} />
            <div style={{ display: 'flex', gap: '8px', marginTop: '12px' }}>
              <div className="skeleton" style={{ width: '60%', height: '36px', borderRadius: '8px' }} />
              <div className="skeleton" style={{ width: '40%', height: '36px', borderRadius: '8px' }} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (variant === 'timeline') {
    return (
      <div className="timeline-list">
        {items.map((i) => (
          <div key={i} className="timeline-item" style={{ borderLeftColor: 'rgba(255,255,255,0.08)' }}>
            <div className="skeleton skeleton-text" style={{ width: '45%', height: '14px' }} />
            <div className="skeleton skeleton-text" style={{ width: '70%', height: '12px', marginTop: '10px' }} />
            <div className="skeleton skeleton-text" style={{ width: '55%', height: '12px', marginTop: '6px' }} />
          </div>
        ))}
      </div>
    );
  }

  // Default: text lines
  return (
    <div>
      {items.map((i) => (
        <div key={i} className="skeleton skeleton-text" style={{ marginBottom: '10px' }} />
      ))}
    </div>
  );
}

export default SkeletonLoader;
