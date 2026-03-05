import { useEffect } from 'react';

export default function Toast({ type = 'info', message, onClose, duration = 4000 }) {
  useEffect(() => {
    if (!onClose) return;
    const timer = setTimeout(onClose, duration);
    return () => clearTimeout(timer);
  }, [onClose, duration]);

  return (
    <div className="toast-container">
      <div className={`toast toast--${type}`}>
        <span>{message}</span>
        {onClose && (
          <button className="toast-close" onClick={onClose}>&times;</button>
        )}
      </div>
    </div>
  );
}
