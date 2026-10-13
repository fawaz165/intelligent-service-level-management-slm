/**
 * SlaDashboard.jsx — Intelligent SLA Monitoring & Risk Prediction Dashboard.
 *
 * Provides real-time visibility into SLA compliance, deterministic breach detection,
 * service health breakdowns, and on-demand DeepSeek-R1 1.5B qualitative predictions.
 */

import { useState, useEffect, useCallback } from 'react';
import { getSlaMetrics, getSlaRisks, predictSlaRisk } from '../services/api';

export default function SlaDashboard() {
  const [metrics, setMetrics] = useState(null);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);

  // Filters
  const [riskFilter, setRiskFilter] = useState('ALL'); // ALL, BREACHED, CRITICAL, HIGH, MEDIUM, LOW
  const [entityFilter, setEntityFilter] = useState('ALL'); // ALL, TICKET, INCIDENT
  const [serviceFilter, setServiceFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  // AI Prediction state
  const [aiAnalyzingId, setAiAnalyzingId] = useState(null);
  const [aiResults, setAiResults] = useState({});

  const fetchData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const [metricsData, risksData] = await Promise.all([
        getSlaMetrics(),
        getSlaRisks({
          include_resolved: true,
        }),
      ]);
      setMetrics(metricsData);
      setItems(risksData);
    } catch (err) {
      setError(err.message || 'Failed to load SLA monitoring data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(() => fetchData(true), 30000);
    return () => clearInterval(interval);
  }, [fetchData]);

  // Trigger on-demand DeepSeek-R1 analysis for an item
  async function handleAnalyzeWithAi(item) {
    const key = `${item.entity_type}_${item.id || item.entity_id}`;
    setAiAnalyzingId(key);

    try {
      const enriched = await predictSlaRisk(item.entity_type, item.id || item.entity_id);
      setAiResults(prev => ({
        ...prev,
        [key]: enriched.ml_prediction || {
          ai_root_cause_analysis: 'Analysis generated from rule-based parameters.',
          ai_recommended_action: enriched.recommended_action,
          risk_trajectory: 'Active Escalation',
        },
      }));
    } catch (err) {
      setAiResults(prev => ({
        ...prev,
        [key]: {
          error: `AI analysis failed: ${err.message}`,
        },
      }));
    } finally {
      setAiAnalyzingId(null);
    }
  }

  // Filter items in memory for instant responsiveness
  const filteredItems = items.filter(item => {
    // Risk filter
    if (riskFilter === 'BREACHED' && !item.is_breached) return false;
    if (riskFilter !== 'ALL' && riskFilter !== 'BREACHED' && item.risk_level.toUpperCase() !== riskFilter) {
      return false;
    }

    // Entity filter
    if (entityFilter === 'TICKET' && item.entity_type !== 'ticket') return false;
    if (entityFilter === 'INCIDENT' && item.entity_type !== 'incident') return false;

    // Service filter
    if (serviceFilter && (item.service_name || '').toLowerCase() !== serviceFilter.toLowerCase()) {
      return false;
    }

    // Search query
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      const matchTitle = (item.title || '').toLowerCase().includes(q);
      const matchId = (item.entity_id || '').toLowerCase().includes(q);
      const matchAssignee = (item.assigned_to || '').toLowerCase().includes(q);
      const matchService = (item.service_name || '').toLowerCase().includes(q);
      if (!matchTitle && !matchId && !matchAssignee && !matchService) return false;
    }

    return true;
  });

  return (
    <div className="sla-dashboard">
      {/* Dashboard Header */}
      <div className="sla-header">
        <div className="sla-header-left">
          <div className="sla-badge-live">
            <span className="live-dot" /> LIVE MONITOR
          </div>
          <h2 className="sla-title">SLA Monitoring & Risk Prediction</h2>
          <p className="sla-subtitle">
            Deterministic breach detection • DeepSeek-R1 1.5B root-cause synthesis • Active queue telemetry
          </p>
        </div>
        <div className="sla-header-actions">
          <button
            className={`btn-sla-refresh ${refreshing ? 'rotating' : ''}`}
            onClick={() => fetchData(true)}
            disabled={loading || refreshing}
          >
            🔄 {refreshing ? 'Refreshing…' : 'Refresh Telemetry'}
          </button>
        </div>
      </div>

      {error && (
        <div className="sla-alert-error">
          ⚠️ {error} — Ensure the ISLM backend is running on port 8000.
        </div>
      )}

      {/* KPI Summary Cards */}
      {metrics && (
        <div className="sla-kpi-grid">
          <div className="sla-kpi-card">
            <div className="sla-kpi-label">Active Monitored</div>
            <div className="sla-kpi-value">{metrics.total_monitored}</div>
            <div className="sla-kpi-detail">
              <span>{metrics.by_entity?.tickets?.total || 0} Tickets</span> •{' '}
              <span>{metrics.by_entity?.incidents?.total || 0} Incidents</span>
            </div>
          </div>

          <div className="sla-kpi-card card-breached">
            <div className="sla-kpi-label">SLA Breaches</div>
            <div className="sla-kpi-value value-critical">{metrics.breached_count}</div>
            <div className="sla-kpi-detail">
              <span className="badge badge-critical">Immediate Action Required</span>
            </div>
          </div>

          <div className="sla-kpi-card card-atrisk">
            <div className="sla-kpi-label">At Risk Items</div>
            <div className="sla-kpi-value value-high">{metrics.at_risk_count}</div>
            <div className="sla-kpi-detail">
              <span>{metrics.critical_count} Critical</span> •{' '}
              <span>{metrics.high_count} High</span>
            </div>
          </div>

          <div className="sla-kpi-card card-compliant">
            <div className="sla-kpi-label">On Track / Healthy</div>
            <div className="sla-kpi-value value-compliant">{metrics.compliant_count}</div>
            <div className="sla-kpi-detail">
              <span>{metrics.medium_count} Moderate</span> •{' '}
              <span>{metrics.low_count} Low Risk</span>
            </div>
          </div>

          <div className="sla-kpi-card card-compliance-rate">
            <div className="sla-kpi-label">Compliance Rate</div>
            <div className="sla-kpi-value">
              {metrics.compliance_rate}%
            </div>
            <div className="sla-gauge-track">
              <div
                className="sla-gauge-fill"
                style={{
                  width: `${Math.min(100, metrics.compliance_rate)}%`,
                  backgroundColor: metrics.compliance_rate > 80 ? '#10b981' : metrics.compliance_rate > 50 ? '#f59e0b' : '#ef4444',
                }}
              />
            </div>
          </div>
        </div>
      )}

      {/* Service Health Breakdown */}
      {metrics?.by_service && (
        <div className="sla-section">
          <div className="sla-section-title">
            <span>🏢 Service Health Telemetry</span>
            {serviceFilter && (
              <button className="btn-clear-filter" onClick={() => setServiceFilter('')}>
                Clear service filter ({serviceFilter})
              </button>
            )}
          </div>
          <div className="sla-service-grid">
            {metrics.by_service.map(svc => {
              const isSelected = serviceFilter.toLowerCase() === svc.service_name.toLowerCase();
              const healthRatio = svc.total > 0 ? Math.round(((svc.total - svc.breached) / svc.total) * 100) : 100;
              return (
                <div
                  key={svc.service_name}
                  className={`sla-service-card ${isSelected ? 'selected' : ''}`}
                  onClick={() => setServiceFilter(isSelected ? '' : svc.service_name)}
                >
                  <div className="sla-service-card-header">
                    <span className="sla-service-name">{svc.service_name}</span>
                    <span className={`badge ${svc.breached > 0 ? 'badge-critical' : 'badge-low'}`}>
                      {svc.breached > 0 ? `${svc.breached} Breached` : 'Compliant'}
                    </span>
                  </div>
                  <div className="sla-service-stats">
                    <span>Total: {svc.total}</span>
                    <span>Critical: {svc.critical}</span>
                    <span>Health: {healthRatio}%</span>
                  </div>
                  <div className="sla-gauge-track mini">
                    <div
                      className="sla-gauge-fill"
                      style={{
                        width: `${healthRatio}%`,
                        backgroundColor: healthRatio > 80 ? '#10b981' : healthRatio > 50 ? '#f59e0b' : '#ef4444',
                      }}
                    />
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div className="sla-controls-bar">
        <div className="sla-filter-tabs">
          {[
            { id: 'ALL', label: 'All Items' },
            { id: 'BREACHED', label: '🚨 Breached' },
            { id: 'CRITICAL', label: 'Critical Risk' },
            { id: 'HIGH', label: 'High Risk' },
            { id: 'MEDIUM', label: 'Medium Risk' },
            { id: 'LOW', label: 'Low Risk' },
          ].map(tab => (
            <button
              key={tab.id}
              className={`sla-filter-tab ${riskFilter === tab.id ? 'active' : ''}`}
              onClick={() => setRiskFilter(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <div className="sla-filter-controls-right">
          <select
            className="sla-select-entity"
            value={entityFilter}
            onChange={e => setEntityFilter(e.target.value)}
          >
            <option value="ALL">All Entities</option>
            <option value="TICKET">Tickets Only</option>
            <option value="INCIDENT">Incidents Only</option>
          </select>

          <input
            type="text"
            className="sla-search-input"
            placeholder="Search items, titles, assignees…"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Monitored Items List */}
      <div className="sla-items-container">
        {loading && items.length === 0 ? (
          <div className="sla-loading-state">
            <div className="loading-spinner" />
            <p>Evaluating SLA telemetry and calculating breach risk models…</p>
          </div>
        ) : filteredItems.length === 0 ? (
          <div className="sla-empty-state">
            <span className="sla-empty-icon">✅</span>
            <h4>No items found matching the selected criteria</h4>
            <p>All monitored items in this filter view are compliant or non-existent.</p>
          </div>
        ) : (
          <div className="sla-items-list">
            {filteredItems.map(item => {
              const itemKey = `${item.entity_type}_${item.id || item.entity_id}`;
              const isAiAnalyzing = aiAnalyzingId === itemKey;
              const aiData = aiResults[itemKey];

              // Calculate progress bar percentage (cap visual display at 100%)
              const visualPercent = Math.min(100, Math.max(2, item.percent_elapsed || 0));
              const isBreached = item.is_breached;
              const riskLevel = (item.risk_level || 'low').toLowerCase();

              return (
                <div key={itemKey} className={`sla-item-card risk-border-${riskLevel}`}>
                  {/* Top Header */}
                  <div className="sla-item-top">
                    <div className="sla-item-identifiers">
                      <span className={`badge badge-entity badge-${item.entity_type}`}>
                        {item.entity_type === 'incident' ? 'Incident' : 'Ticket'}
                      </span>
                      <span className="sla-item-id">{item.entity_id}</span>
                      <span className={`badge badge-${(item.priority || 'medium').toLowerCase()}`}>
                        {item.priority?.toUpperCase()}
                      </span>
                      <span className={`badge badge-${riskLevel}`}>
                        {item.risk_level?.toUpperCase()} RISK
                      </span>
                      {isBreached && <span className="badge badge-breached">SLA BREACHED</span>}
                      {item.status_label === 'Imminent Breach' && (
                        <span className="badge badge-imminent_breach">IMMINENT BREACH</span>
                      )}
                    </div>

                    <div className="sla-item-meta-right">
                      <span className="sla-service-tag">🏢 {item.service_name}</span>
                      <span className="sla-assignee-tag">👤 {item.assigned_to || 'Unassigned'}</span>
                    </div>
                  </div>

                  {/* Title */}
                  <h3 className="sla-item-title">{item.title}</h3>

                  {/* Progress Bar & Telemetry Details */}
                  <div className="sla-progress-block">
                    <div className="sla-progress-labels">
                      <span>
                        <strong>Elapsed:</strong> {item.elapsed_minutes != null ? `${item.elapsed_minutes}m` : '—'} (
                        <strong>{item.percent_elapsed}%</strong>)
                      </span>
                      <span>
                        <strong>Target:</strong> {item.resolution_target || '—'} •{' '}
                        {isBreached
                          ? `Exceeded by ${item.elapsed_minutes - (item.target_minutes || 0)}m`
                          : `Remaining: ${item.remaining_minutes || 0}m`}
                      </span>
                    </div>
                    <div className="sla-progress-track">
                      <div
                        className={`sla-progress-fill fill-${riskLevel} ${isBreached ? 'fill-breached' : ''}`}
                        style={{ width: `${visualPercent}%` }}
                      />
                    </div>
                  </div>

                  {/* Explainable Reasons & Recommended Actions */}
                  <div className="sla-item-reason-box">
                    <div className="sla-reason-row">
                      <span className="sla-reason-tag tag-deterministic">Rule-Based Detection</span>
                      <span className="sla-reason-text">{item.reason}</span>
                    </div>
                    <div className="sla-action-row">
                      <span className="sla-reason-tag tag-action">Action Required</span>
                      <span className="sla-action-text">{item.recommended_action}</span>
                    </div>
                  </div>

                  {/* AI Prediction Section */}
                  <div className="sla-ai-section">
                    {!aiData ? (
                      <button
                        className="btn-ai-predict"
                        onClick={() => handleAnalyzeWithAi(item)}
                        disabled={isAiAnalyzing}
                      >
                        {isAiAnalyzing ? '🤖 DeepSeek-R1 Synthesizing Root Cause…' : '🤖 Run DeepSeek-R1 AI Risk Synthesis'}
                      </button>
                    ) : aiData.error ? (
                      <div className="sla-ai-error">
                        ⚠️ {aiData.error}
                      </div>
                    ) : (
                      <div className="sla-ai-panel">
                        <div className="sla-ai-panel-header">
                          <span className="badge badge-ai">DeepSeek-R1 1.5B Qualitative Synthesis</span>
                          <span className="sla-ai-trajectory">
                            Trajectory: <strong>{aiData.risk_trajectory || 'Active'}</strong>
                          </span>
                        </div>
                        <div className="sla-ai-content">
                          <p>
                            <strong>Root Cause Analysis:</strong> {aiData.ai_root_cause_analysis}
                          </p>
                          <p>
                            <strong>Action Plan:</strong> {aiData.ai_recommended_action}
                          </p>
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
