/**
 * ChatMessage — renders a single user or AI message.
 *
 * AI messages reveal with a typewriter effect. Includes structured data tables.
 */
import { useState, useEffect, useRef } from 'react';
import DataTable from './DataTable';

function formatTime(date) {
  return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

/** Typewriter hook — reveals text character by character */
function useTypewriter(text, speed = 12, enabled = true) {
  const [displayed, setDisplayed] = useState(enabled ? '' : text);
  const [done, setDone] = useState(!enabled);
  const indexRef = useRef(0);

  useEffect(() => {
    if (!enabled) {
      setDisplayed(text);
      setDone(true);
      return;
    }

    setDisplayed('');
    setDone(false);
    indexRef.current = 0;

    const interval = setInterval(() => {
      indexRef.current += 1;
      // Reveal in small chunks (2-4 chars) for a natural feel
      const chunk = Math.min(indexRef.current * 2, text.length);
      setDisplayed(text.slice(0, chunk));

      if (chunk >= text.length) {
        setDone(true);
        clearInterval(interval);
      }
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed, enabled]);

  return { displayed, done };
}

export default function ChatMessage({ msg }) {
  const isUser = msg.role === 'user';
  const shouldStream = msg.role === 'ai' && msg.streaming !== false;

  const { displayed, done } = useTypewriter(msg.text || '', 14, shouldStream);

  return (
    <div className={`message ${isUser ? 'user' : 'ai'}`}>
      <div className="message-avatar">
        {isUser ? (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/>
            <circle cx="12" cy="7" r="4"/>
          </svg>
        ) : (
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 2L2 7l10 5 10-5-10-5z"/>
            <path d="M2 17l10 5 10-5"/>
            <path d="M2 12l10 5 10-5"/>
          </svg>
        )}
      </div>
      <div className="message-body">
        <div className="message-content">
          <span>{displayed}</span>
          {!done && <span className="typing-cursor" />}
        </div>

        {/* Render data table after text finishes streaming */}
        {done && msg.data && msg.data.length > 0 && (
          <div className="table-reveal">
            <DataTable data={msg.data} dataType={msg.dataType} />
          </div>
        )}

        <div className="message-time">{formatTime(msg.timestamp)}</div>
      </div>
    </div>
  );
}
