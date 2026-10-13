/**
 * API service module — all backend communication goes through here.
 *
 * Uses Server-Sent Events (SSE) for chat responses to avoid long-hanging requests.
 */

const API_BASE = '/api';

/**
 * Send a chat message via SSE streaming.
 * Calls `onStatus` for progress updates, and resolves with the final result.
 *
 * @param {string} message - The user's natural language message
 * @param {function} onStatus - Callback receiving status strings (e.g. "Processing...")
 * @returns {Promise<Object>} Final ChatResponse with data/tables
 */
export function sendMessageStreaming(message, onStatus) {
  return new Promise((resolve, reject) => {
    const url = `${API_BASE}/chat/stream?message=${encodeURIComponent(message)}`;
    const eventSource = new EventSource(url);

    eventSource.addEventListener('status', (e) => {
      try {
        const { status } = JSON.parse(e.data);
        if (onStatus) onStatus(status);
      } catch {
        // ignore
      }
    });

    eventSource.addEventListener('result', (e) => {
      try {
        const result = JSON.parse(e.data);
        resolve(result);
      } catch (err) {
        reject(new Error('Failed to parse server result'));
      }
    });

    eventSource.addEventListener('done', () => {
      eventSource.close();
    });

    eventSource.onerror = (err) => {
      eventSource.close();
      reject(new Error('Connection to server lost. Make sure the backend is running.'));
    };

    // Safety timeout — close after 2 minutes if still open
    setTimeout(() => {
      if (eventSource.readyState !== EventSource.CLOSED) {
        eventSource.close();
        reject(new Error('Request timed out'));
      }
    }, 120_000);
  });
}


/**
 * Send a non-streaming chat message (used for confirmations).
 * @param {string} message - The user's natural language message
 * @param {string|null} confirmAction - JSON string of pending action to confirm
 * @returns {Promise<Object>} ChatResponse
 */
export async function sendMessage(message, confirmAction = null) {
  const body = { message };
  if (confirmAction) {
    body.confirm_action = JSON.stringify(confirmAction);
  }

  const res = await fetch(`${API_BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Server error (${res.status})`);
  }

  return res.json();
}

/**
 * Get system health status.
 * @returns {Promise<Object>} Health status
 */
export async function getHealth() {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Health check failed');
  return res.json();
}

/**
 * Upload a file.
 * @param {File} file - File object from input
 * @returns {Promise<Object>} File metadata
 */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append('file', file);

  const res = await fetch(`${API_BASE}/files/upload`, {
    method: 'POST',
    body: formData,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Upload failed (${res.status})`);
  }

  return res.json();
}

/**
 * Get aggregate SLA dashboard metrics.
 * @returns {Promise<Object>} Metrics summary
 */
export async function getSlaMetrics() {
  const res = await fetch(`${API_BASE}/sla/metrics`);
  if (!res.ok) throw new Error('Failed to fetch SLA metrics');
  return res.json();
}

/**
 * Get evaluated SLA risks with optional filters.
 * @param {Object} params - Query filters { risk_level, entity, service, breached_only, include_resolved }
 * @returns {Promise<Array>} Monitored items with SLA risks
 */
export async function getSlaRisks(params = {}) {
  const query = new URLSearchParams();
  if (params.risk_level) query.append('risk_level', params.risk_level);
  if (params.entity) query.append('entity', params.entity);
  if (params.service) query.append('service', params.service);
  if (params.breached_only) query.append('breached_only', 'true');
  if (params.include_resolved) query.append('include_resolved', 'true');

  const qs = query.toString();
  const url = `${API_BASE}/sla/risks${qs ? `?${qs}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch SLA risk data');
  return res.json();
}

/**
 * On-demand DeepSeek-R1 1.5B qualitative root cause prediction and technical action plan.
 * @param {string} entityType - "ticket" or "incident"
 * @param {string|number} id - Target ID
 * @returns {Promise<Object>} Enriched item with ML prediction
 */
export async function predictSlaRisk(entityType, id) {
  const res = await fetch(`${API_BASE}/sla/predict`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ entity_type: entityType, id: String(id) }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Risk prediction failed (${res.status})`);
  }
  return res.json();
}
