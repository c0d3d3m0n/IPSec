import React from 'react';

/**
 * StatusDot — animated pulsing status indicator.
 *
 * @param {'online'|'offline'|'inactive'} status
 * @param {string} label   Optional text label next to the dot
 * @param {string} className  Optional extra class
 */
function StatusDot({ status = 'inactive', label, className = '' }) {
  const dotClass = status === 'online'
    ? 'online'
    : status === 'offline'
      ? 'offline'
      : 'inactive';

  return (
    <span className={`status-indicator ${className}`}>
      <span className={`status-dot ${dotClass}`} />
      {label ? <span className="status-label">{label}</span> : null}
    </span>
  );
}

export default StatusDot;
