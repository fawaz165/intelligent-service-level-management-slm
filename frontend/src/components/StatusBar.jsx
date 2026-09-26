/**
 * StatusBar — displays system connection status.
 */
import { useState, useEffect } from 'react';
import { getHealth } from '../services/api';

export default function StatusBar() {
  const [health, setHealth] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function check() {
      try {
        const data = await getHealth();
        if (mounted) setHealth(data);
      } catch {
        if (mounted) setHealth(null);
      }
    }

    check();
    const interval = setInterval(check, 15000); // Re-check every 15s
    return () => { mounted = false; clearInterval(interval); };
  }, []);

  const ollamaConnected = health?.ollama?.connected ?? false;
  const modelAvailable = health?.ollama?.model_available ?? false;
  const dbConnected = health?.database?.connected ?? false;

  return (
    <div className="status-bar">
      <div className="status-item">
        <span className="status-label">SLM:</span>
        <span className="status-value">{health?.slm || 'deepseek-r1:1.5b'}</span>
      </div>

      <div className="status-item">
        <span className="status-label">Runtime:</span>
        <span className="status-value">{health?.runtime || 'Ollama'}</span>
      </div>

      <div className="status-item">
        <span className={`status-dot ${ollamaConnected ? (modelAvailable ? 'connected' : 'warning') : 'disconnected'}`} />
        <span className="status-label">Ollama:</span>
        <span className="status-value">
          {ollamaConnected ? (modelAvailable ? 'Connected' : 'Model Missing') : 'Disconnected'}
        </span>
      </div>

      <div className="status-item">
        <span className={`status-dot ${dbConnected ? 'connected' : 'disconnected'}`} />
        <span className="status-label">Database:</span>
        <span className="status-value">
          {dbConnected ? `Connected (${health?.database?.type || 'SQLite'})` : 'Disconnected'}
        </span>
      </div>
    </div>
  );
}
