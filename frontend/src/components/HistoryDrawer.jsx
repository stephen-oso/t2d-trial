import { useEffect } from 'react';

function formatDate(iso) {
  return new Date(iso).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default function HistoryDrawer({ open, history, onClose, onRestore, onClear }) {
  useEffect(() => {
    function onKey(e) { if (e.key === 'Escape') onClose(); }
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [onClose]);

  return (
    <>
      <div
        className={`drawer-overlay${open ? ' drawer-overlay--open' : ''}`}
        onClick={onClose}
      />
      <aside className={`drawer${open ? ' drawer--open' : ''}`}>
        <div className="drawer__header">
          <span className="drawer__title">Recent Searches</span>
          <button className="drawer__close" onClick={onClose} aria-label="Close">×</button>
        </div>

        <div className="drawer__list">
          {history.length === 0 ? (
            <p className="drawer__empty">No searches yet.</p>
          ) : (
            history.map(entry => (
              <button
                key={entry.id}
                className="drawer__item"
                onClick={() => onRestore(entry)}
              >
                <p className="drawer__item-snippet">{entry.snippet}</p>
                <p className="drawer__item-meta">
                  {entry.matchCount} trial{entry.matchCount !== 1 ? 's' : ''} · {formatDate(entry.timestamp)}
                </p>
              </button>
            ))
          )}
        </div>

        {history.length > 0 && (
          <div className="drawer__footer">
            <button className="drawer__clear" onClick={onClear}>Clear history</button>
          </div>
        )}
      </aside>
    </>
  );
}
