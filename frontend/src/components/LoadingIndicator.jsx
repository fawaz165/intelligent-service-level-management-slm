/**
 * LoadingIndicator — animated pulse shown while waiting for AI response.
 * Shows real-time status text from the backend SSE stream.
 */
export default function LoadingIndicator({ statusText }) {
  return (
    <div className="message ai">
      <div className="message-avatar">
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M12 2L2 7l10 5 10-5-10-5z"/>
          <path d="M2 17l10 5 10-5"/>
          <path d="M2 12l10 5 10-5"/>
        </svg>
      </div>
      <div className="message-body">
        <div className="message-content">
          <div className="loading-indicator">
            <div className="loading-dots">
              <div className="loading-dot" />
              <div className="loading-dot" />
              <div className="loading-dot" />
            </div>
            <span className="loading-text">{statusText || 'Thinking…'}</span>
          </div>
        </div>
      </div>
    </div>
  );
}
