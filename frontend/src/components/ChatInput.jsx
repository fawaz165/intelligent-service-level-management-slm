/**
 * ChatInput — text input with send button and file upload.
 */
import { useState, useRef } from 'react';

export default function ChatInput({ onSend, onFileUpload, disabled }) {
  const [text, setText] = useState('');
  const fileRef = useRef(null);

  function handleSend() {
    const trimmed = text.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setText('');
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleFileChange(e) {
    const file = e.target.files?.[0];
    if (file && onFileUpload) {
      onFileUpload(file);
      e.target.value = '';
    }
  }

  return (
    <div className="chat-input-area">
      <div className="chat-input-wrapper">
        {/* Hidden file input */}
        <input
          type="file"
          ref={fileRef}
          onChange={handleFileChange}
          style={{ display: 'none' }}
        />

        {/* Upload button */}
        <button
          className="btn-clear"
          onClick={() => fileRef.current?.click()}
          disabled={disabled}
          title="Upload file"
          style={{ border: 'none', padding: '4px 8px', fontSize: '18px' }}
        >
          📎
        </button>

        <textarea
          className="chat-input"
          placeholder="Ask me about tickets, services, or files…"
          value={text}
          onChange={e => setText(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={disabled}
          rows={1}
        />

        <button
          className="btn-send"
          onClick={handleSend}
          disabled={disabled || !text.trim()}
          title="Send message"
        >
          ▶
        </button>
      </div>
    </div>
  );
}
