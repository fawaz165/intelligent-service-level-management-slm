/**
 * App.jsx — Main ISLM Application
 *
 * Orchestrates Chat Assistant & SLA Monitoring Dashboard views.
 * Supports SSE streaming chat, natural language operations, and real-time SLA risk monitoring.
 */
import { useState, useRef, useEffect } from 'react';
import ChatMessage from './components/ChatMessage';
import ChatInput from './components/ChatInput';
import StatusBar from './components/StatusBar';
import LoadingIndicator from './components/LoadingIndicator';
import ConfirmDialog from './components/ConfirmDialog';
import SlaDashboard from './components/SlaDashboard';
import { sendMessageStreaming, sendMessage, uploadFile, getSlaMetrics } from './services/api';
import './index.css';

const EXAMPLE_QUERIES = [
  'Show SLA breach risks',
  'Show at-risk tickets',
  'Show all incidents',
  'Show open network incidents',
  'Create a high-priority database ticket',
  'Show SLA records',
];

export default function App() {
  const [activeView, setActiveView] = useState('chat'); // 'chat' or 'sla'
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [statusText, setStatusText] = useState('');
  const [pendingAction, setPendingAction] = useState(null);
  const [confirmMessage, setConfirmMessage] = useState('');
  const [breachCount, setBreachCount] = useState(null);
  const chatEndRef = useRef(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (activeView === 'chat') {
      chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, loading, activeView]);

  // Periodically fetch breach count for header alert pill
  useEffect(() => {
    let mounted = true;
    async function loadBreachPill() {
      try {
        const m = await getSlaMetrics();
        if (mounted && m) {
          setBreachCount(m.breached_count);
        }
      } catch {
        // ignore
      }
    }
    loadBreachPill();
    const timer = setInterval(loadBreachPill, 20000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, []);

  // ── Send a chat message (with SSE) ──────────────────────────────
  async function handleSend(text) {
    if (activeView !== 'chat') {
      setActiveView('chat');
    }

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

        {/* Navigation Switcher */}
        <div className="nav-switcher">
          <button
            className={`nav-btn ${activeView === 'chat' ? 'active' : ''}`}
            onClick={() => setActiveView('chat')}
          >
            💬 Chat Assistant
          </button>
          <button
            className={`nav-btn ${activeView === 'sla' ? 'active' : ''}`}
            onClick={() => setActiveView('sla')}
          >
            📊 SLA Monitoring Dashboard
            {breachCount != null && breachCount > 0 && (
              <span className="breach-pill">{breachCount} Breached</span>
            )}
          </button>
        </div>

        <div className="header-actions">
          {activeView === 'chat' ? (
            <button className="btn-clear" onClick={handleClear}>
              🗑️ Clear Chat
            </button>
          ) : (
            <button className="btn-clear" onClick={() => setActiveView('chat')}>
              💬 Open Chat
            </button>
          )}
        </div>
      </header>

      {/* Status Bar */}
      <StatusBar />

      {/* View Content */}
      {activeView === 'sla' ? (
        <SlaDashboard />
      ) : (
        <>
          {/* Chat Area */}
          <div className="chat-area">
            {messages.length === 0 ? (
              <div className="welcome">
                <div className="welcome-icon">🛡️</div>
                <div className="welcome-title">Welcome to ISLM</div>
                <div className="welcome-text">
                  Manage IT service tickets, network incidents, and SLAs with natural language.
                  Run automated SLA breach detection and DeepSeek-R1 risk predictions:
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
        </>
      )}

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
