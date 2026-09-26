/**
 * App.jsx — Main ISLM Chat Application
 *
 * Orchestrates the chat flow: user input → SSE → status updates → result display.
 * Manages confirmation dialogs for destructive operations.
 */
import { useState, useRef, useEffect } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import StatusBar from './components/StatusBar';
import LoadingIndicator from './components/LoadingIndicator';
import ConfirmDialog from './components/ConfirmDialog';
import { sendMessageStreaming, sendMessage, uploadFile } from './services/api';
import './index.css';

const EXAMPLE_QUERIES = [
  'Show all open network tickets',
  'Create a high-priority database ticket',
  'Show all services',
  'List uploaded files',
  'Show SLA records',
];

export default function App() {
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [pendingAction, setPendingAction] = useState(null);
  const [confirmMessage, setConfirmMessage] = useState('');
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  // ── Send a chat message (with SSE) ──────────────────────────────
  async function handleSend(text) {
    // Add user message
    const userMsg = {
      id: Date.now(),
      role: 'user',
      text,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, userMsg]);
    setLoading(true);
    setStatusText('Connecting...');

    try {
      const result = await sendMessageStreaming(text, (status) => {
        setStatusText(status);
      });

      // Build AI message from the result
      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: result.reply,
        data: result.data,
        dataType: result.data_type,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);

      // Handle confirmation requirement
      if (result.requires_confirmation && result.pending_action) {
        setPendingAction(result.pending_action);
        setConfirmMessage(result.reply);
      }
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: `⚠️ Error: ${err.message}. Make sure the backend is running on port 8000.`,
        streaming: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
      setStatusText('');
    }
  }

  // ── Handle confirmation ─────────────────────────────────────────
  async function handleConfirm() {
    if (!pendingAction) return;

    setLoading(true);
    setPendingAction(null);
    setConfirmMessage('');

    try {
      const res = await sendMessage('confirm', pendingAction);
      const aiMsg = {
        id: Date.now(),
        role: 'ai',
        text: res.reply,
        data: res.data,
        dataType: res.data_type,
        streaming: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now(),
        role: 'ai',
        text: `⚠️ Error during confirmation: ${err.message}`,
        streaming: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  function handleCancel() {
    setPendingAction(null);
    setConfirmMessage('');

    const cancelMsg = {
      id: Date.now(),
      role: 'ai',
      text: '🚫 Operation cancelled.',
      streaming: false,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, cancelMsg]);
  }

  // ── Handle file upload ──────────────────────────────────────────
  async function handleFileUpload(file) {
    const uploadMsg = {
      id: Date.now(),
      role: 'user',
      text: `📎 Uploading file: ${file.name}`,
      timestamp: new Date(),
    };
    setMessages(prev => [...prev, uploadMsg]);
    setLoading(true);

    try {
      const result = await uploadFile(file);
      const aiMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: `✅ File "${result.file_name}" uploaded successfully (${result.file_size_display}).`,
        data: [result],
        dataType: 'files',
        streaming: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, aiMsg]);
    } catch (err) {
      const errorMsg = {
        id: Date.now() + 1,
        role: 'ai',
        text: `⚠️ Upload failed: ${err.message}`,
        streaming: false,
        timestamp: new Date(),
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  }

  // ── Clear chat ──────────────────────────────────────────────────
  function handleClear() {
    setMessages([]);
    setPendingAction(null);
    setConfirmMessage('');
  }

  // ── Render ──────────────────────────────────────────────────────
  return (
    <div className="app">
      {/* Header */}
      <header className="header">
        <div className="header-brand">
          <div className="header-logo">IS</div>
          <div>
            <div className="header-title">Intelligent Service Level Management</div>
            <div className="header-subtitle">Powered by DeepSeek-R1:1.5B • Local SLM</div>
          </div>
        </div>
        <div className="header-actions">
          <button className="btn-clear" onClick={handleClear}>
            🗑️ Clear Chat
          </button>
        </div>
      </header>

      {/* Status Bar */}
      <StatusBar />

      {/* Chat Area */}
      <div className="chat-area">
        {messages.length === 0 ? (
          <div className="welcome">
            <div className="welcome-icon">🛡️</div>
            <div className="welcome-title">Welcome to ISLM</div>
            <div className="welcome-text">
              I can help you manage IT service tickets, services, SLAs, and files
              using natural language. Try one of these examples:
            </div>
            <div className="welcome-examples">
              {EXAMPLE_QUERIES.map(q => (
                <button
                  key={q}
                  className="welcome-example"
                  onClick={() => handleSend(q)}
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <>
            {messages.map(msg => (
              <ChatMessage key={msg.id} msg={msg} />
            ))}
            {loading && <LoadingIndicator statusText={statusText} />}
          </>
        )}
        <div ref={chatEndRef} />
      </div>

      {/* Chat Input */}
      <ChatInput
        onSend={handleSend}
        onFileUpload={handleFileUpload}
        disabled={loading}
      />

      {/* Confirmation Dialog */}
      {pendingAction && (
        <ConfirmDialog
          message={confirmMessage}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
        />
      )}
    </div>
  );
}
