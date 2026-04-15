import React from 'react';

function ToastStack({ toasts, onDismiss }) {
  return (
    <div className="toast-stack" role="status" aria-live="polite">
      {toasts.map((toast) => (
        <div key={toast.id} className={`toast toast-${toast.type}`}>
          <div className="toast-message">{toast.message}</div>
          <button className="toast-close" onClick={() => onDismiss(toast.id)} aria-label="Dismiss notification">
            x
          </button>
        </div>
      ))}
    </div>
  );
}

export default ToastStack;
