import React, { useState, useCallback } from 'react';

/**
 * HashDisplay — truncated hash with copy-to-clipboard and tooltip.
 *
 * @param {string} hash         Full hash string (e.g. SHA-512)
 * @param {number} truncateAt   Number of visible characters (default 16)
 * @param {string} className    Optional extra class
 */
function HashDisplay({ hash, truncateAt = 16, className = '' }) {
  const [copied, setCopied] = useState(false);
  const [showTooltip, setShowTooltip] = useState(false);

  const handleCopy = useCallback(() => {
    if (!hash) return;
    navigator.clipboard.writeText(hash).then(() => {
      setCopied(true);
      window.setTimeout(() => setCopied(false), 2000);
    });
  }, [hash]);

  if (!hash) return null;

  const truncated = hash.length > truncateAt
    ? `${hash.slice(0, truncateAt)}…`
    : hash;

  return (
    <span
      className={`hash-display ${className}`}
      onMouseEnter={() => setShowTooltip(true)}
      onMouseLeave={() => setShowTooltip(false)}
    >
      <code className="hash-value mono-text">{truncated}</code>
      <button
        className="hash-copy-btn"
        onClick={handleCopy}
        aria-label="Copy full hash"
        type="button"
      >
        {copied ? '✓' : '⧉'}
      </button>
      {showTooltip && (
        <span className="hash-tooltip mono-text">{hash}</span>
      )}
    </span>
  );
}

export default HashDisplay;
