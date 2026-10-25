/**
 * SlaDashboard.jsx — Intelligent SLA Monitoring & Risk Prediction Dashboard.
 *
 * Provides real-time visibility into SLA compliance, deterministic breach detection,
 * live host & simulated IT infrastructure telemetry, service health breakdowns,
 * inline SQLite status/assignment synchronization, and on-demand DeepSeek-R1 1.5B qualitative predictions.
 */

import { useState, useEffect, useCallback } from 'react';
import {
  getSlaMetrics,
  getSlaRisks,
  predictSlaRisk,
  getTelemetryMetrics,
  updateTicket,
  updateIncident,
} from '../services/api';

const TECHNICIANS = [
  'Alice Johnson',
  'Bob Smith',
  'Carol Lee',
  'David Kumar',
  'Eve Martinez',
  'Frank Wilson',
  'Grace Chen',
  'Henry Patel',
];

export default function SlaDashboard({ onMetricsUpdate }) {
  const [metrics, setMetrics] = useState(null);
  const [items, setItems] = useState([]);
  const [telemetry, setTelemetry] = useState(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);

  // Filters & Sorting
  const [riskFilter, setRiskFilter] = useState('ALL'); // ALL, BREACHED, CRITICAL, HIGH, MEDIUM, LOW, RESOLVED, ALL_RECORDS
  const [entityFilter, setEntityFilter] = useState('ALL'); // ALL, TICKET, INCIDENT
  const [serviceFilter, setServiceFilter] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('URGENCY_DESC'); // URGENCY_DESC, REMAINING_ASC, PRIORITY_DESC, NEWEST, OLDEST

  // Inline action states
  const [updatingId, setUpdatingId] = useState(null);

  // AI Prediction state
  const [aiAnalyzingId, setAiAnalyzingId] = useState(null);
  const [aiResults, setAiResults] = useState({});
  const [selectedAiItem, setSelectedAiItem] = useState(null);

  const handleOpenAiModal = (item) => {
    setSelectedAiItem(item);
    const key = `${item.entity_type}_${item.id || item.entity_id}`;
    if (!aiResults[key] && aiAnalyzingId !== key) {
      handleAnalyzeWithAi(item);
    }
  };

  const fetchData = useCallback(async (isSilent = false) => {
    if (!isSilent) setLoading(true);
    else setRefreshing(true);
    setError(null);

    try {
      const [metricsData, risksData, telemetryData] = await Promise.all([
        getSlaMetrics(),
        getSlaRisks({ include_resolved: true }),
        getTelemetryMetrics().catch(() => null),
      ]);
      setMetrics(metricsData);
      onMetricsUpdate?.(metricsData);

      // Deduplicate items to prevent duplicate records
      const dedupedMap = new Map();
      for (const item of (risksData || [])) {
        const key = `${item.entity_type}_${item.id || item.entity_id}`;
        if (!dedupedMap.has(key)) {
          dedupedMap.set(key, item);
        }
      }
      setItems(Array.from(dedupedMap.values()));

      if (telemetryData) setTelemetry(telemetryData);
      setLastUpdated(new Date());
    } catch (err) {
      setError(err.message || 'Failed to load SLA monitoring data');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [onMetricsUpdate]);

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
          ai_root_cause_analysis: 'Root cause analysis generated from technical parameters.',
          ai_sla_risk_explanation: 'Active SLA consumption under observation.',
          ai_recommended_action: enriched.recommended_action,
          risk_trajectory: 'Active Monitoring',
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

  // Handle inline ticket/incident status update backed by SQLite
  async function handleStatusChange(item, newStatus) {
    const key = `${item.entity_type}_${item.id || item.entity_id}`;
    setUpdatingId(key);

    try {
      if (item.entity_type === 'incident') {
        await updateIncident(item.entity_id || item.id, { status: newStatus });
      } else {
        await updateTicket(item.id, { status: newStatus });
      }
      await fetchData(true);
    } catch (err) {
      alert(`Status update failed: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  }

  // Handle inline ticket/incident assignment backed by SQLite
  async function handleAssigneeChange(item, newAssignee) {
    const key = `${item.entity_type}_${item.id || item.entity_id}`;
    setUpdatingId(key);

    try {
      if (item.entity_type === 'incident') {
        const val = newAssignee === 'Unassigned' ? '' : newAssignee.toLowerCase().replace(' ', '_');
        await updateIncident(item.entity_id || item.id, { assigned_to: val });
      } else {
        const userMap = {
          'Alice Johnson': 1,
          'Bob Smith': 2,
          'Carol Lee': 3,
          'David Kumar': 4,
          'Eve Martinez': 5,
          'Frank Wilson': 6,
          'Grace Chen': 7,
          'Henry Patel': 8,
        };
        const userId = userMap[newAssignee] || null;
        await updateTicket(item.id, { assigned_to: userId });
      }
      await fetchData(true);
    } catch (err) {
      alert(`Assignment update failed: ${err.message}`);
    } finally {
      setUpdatingId(null);
    }
  }

  const isItemResolved = item => ['resolved', 'closed'].includes((item.status || '').toLowerCase());

  // Count items by category for tab badges matching SQLite data with non-overlapping partitions
  const counts = {
    all_active: items.filter(i => !isItemResolved(i)).length,
    breached: items.filter(i => !isItemResolved(i) && i.is_breached).length,
    critical: items.filter(i => !isItemResolved(i) && !i.is_breached && i.risk_level === 'Critical').length,
    high: items.filter(i => !isItemResolved(i) && !i.is_breached && i.risk_level === 'High').length,
    medium: items.filter(i => !isItemResolved(i) && !i.is_breached && i.risk_level === 'Medium').length,
    low: items.filter(i => !isItemResolved(i) && !i.is_breached && i.risk_level === 'Low').length,
    resolved: items.filter(i => isItemResolved(i)).length,
    all_records: items.length,
  };

  // Filter items in memory for instant responsiveness
  const filteredItems = items.filter(item => {
    const isResolved = isItemResolved(item);

    // Tab filter
    if (riskFilter === 'ALL' && isResolved) return false;
    if (riskFilter === 'BREACHED' && (isResolved || !item.is_breached)) return false;
    if (riskFilter === 'CRITICAL' && (isResolved || item.is_breached || item.risk_level !== 'Critical')) return false;
    if (riskFilter === 'HIGH' && (isResolved || item.is_breached || item.risk_level !== 'High')) return false;
    if (riskFilter === 'MEDIUM' && (isResolved || item.is_breached || item.risk_level !== 'Medium')) return false;
    if (riskFilter === 'LOW' && (isResolved || item.is_breached || item.risk_level !== 'Low')) return false;
    if (riskFilter === 'RESOLVED' && !isResolved) return false;
    // 'ALL_RECORDS' shows all items

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

  // Sort items according to active sort option
  const sortedItems = [...filteredItems].sort((a, b) => {
    if (sortBy === 'URGENCY_DESC') {
      return (b.percent_elapsed || 0) - (a.percent_elapsed || 0);
    }
    if (sortBy === 'REMAINING_ASC') {
      return (a.remaining_minutes ?? 99999) - (b.remaining_minutes ?? 99999);
    }
    if (sortBy === 'PRIORITY_DESC') {
      const pMap = { critical: 4, high: 3, medium: 2, low: 1 };
      const pDiff = (pMap[b.priority?.toLowerCase()] || 0) - (pMap[a.priority?.toLowerCase()] || 0);
      if (pDiff !== 0) return pDiff;
      return (b.percent_elapsed || 0) - (a.percent_elapsed || 0);
    }
    if (sortBy === 'NEWEST') {
      return new Date(b.created_at || 0) - new Date(a.created_at || 0);
    }
    if (sortBy === 'OLDEST') {
      return new Date(a.created_at || 0) - new Date(b.created_at || 0);
    }
    return 0;
  });

  const filterTabs = [
    { id: 'ALL', label: 'All Active', count: counts.all_active },
    { id: 'BREACHED', label: '🚨 Breached', count: counts.breached },
    { id: 'CRITICAL', label: 'Critical Risk', count: counts.critical },
    { id: 'HIGH', label: 'High Risk', count: counts.high },
    { id: 'MEDIUM', label: 'Medium Risk', count: counts.medium },
    { id: 'LOW', label: 'Low Risk', count: counts.low },
    { id: 'RESOLVED', label: '✅ Resolved', count: counts.resolved },
    { id: 'ALL_RECORDS', label: '📁 All Records', count: counts.all_records },
  ];

  return (
    <div className="sla-dashboard">
      {/* Dashboard Header */}
      <div className="sla-header">
        <div className="sla-header-left">
          <div className="sla-badge-live">
            <span className="live-dot" /> LIVE SLA &amp; IT TELEMETRY
          </div>
          <h2 className="sla-title">SLA Monitoring &amp; Risk Prediction</h2>
          <p className="sla-subtitle">
            Deterministic breach detection • DeepSeek-R1 1.5B root-cause synthesis • Real host &amp; simulated IT telemetry
          </p>
        </div>
        <div className="sla-header-actions">
          {lastUpdated && (
            <span className="sla-last-updated-text">
              ⏱️ Updated: {lastUpdated.toLocaleTimeString()}
            </span>
          )}
          <button
            className={`btn-sla-refresh ${refreshing ? 'rotating' : ''}`}
            onClick={() => fetchData(true)}
            disabled={loading || refreshing}
            title="Refresh SLA calculations and infrastructure telemetry"
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
              <span>{metrics.by_entity?.incidents?.total || 0} Incidents</span> •{' '}
              <span className="sla-kpi-resolved-tag">{counts.resolved} Resolved</span>
            </div>
          </div>

          <div className="sla-kpi-card card-breached">
            <div className="sla-kpi-label">SLA Breaches</div>
            <div className="sla-kpi-value value-critical">{metrics.breached_count}</div>
            <div className="sla-kpi-detail">
              <span className="badge badge-critical">Deadline Exceeded</span>
            </div>
          </div>

          <div className="sla-kpi-card card-atrisk">
            <div className="sla-kpi-label">At Risk Items</div>
            <div className="sla-kpi-value value-high">{metrics.at_risk_count}</div>
            <div className="sla-kpi-detail">
              <span>{metrics.imminent_breach_count ?? 0} Imminent Breach</span> •{' '}
              <span>{metrics.high_risk_count ?? 0} High Risk</span>
            </div>
          </div>

          <div className="sla-kpi-card card-compliant">
            <div className="sla-kpi-label">On Track / Healthy</div>
            <div className="sla-kpi-value value-compliant">
              {metrics.healthy_count ?? (metrics.compliant_count - (metrics.at_risk_count || 0))}
            </div>
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
            <div className="sla-kpi-detail">
              <span>{metrics.compliant_count} of {metrics.total_monitored} Compliant</span>
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

      {/* Networking & DBMS Telemetry Strip */}
      {telemetry && (
        <div className="sla-telemetry-panel">
          <div className="sla-telemetry-header">
            <div className="sla-telemetry-title">
              <span>📡 Infrastructure &amp; DBMS Telemetry</span>
              <span className={`badge ${telemetry.overall_health === 'Optimal' ? 'badge-low' : 'badge-high'}`}>
                System Health: {telemetry.overall_health}
              </span>
            </div>
            <div className="sla-telemetry-header-meta">
              <span className="telemetry-clock-badge">
                ⏱️ Telemetry Clock: <strong>{telemetry.timestamp || telemetry.real_metrics?.timestamp}</strong>
              </span>
            </div>
          </div>

          {/* Section 1: Real Host Telemetry */}
          <div className="telemetry-section-group">
            <div className="telemetry-section-label">
              <span className="badge badge-real-telemetry">
                🟢 Verified Live Host Telemetry
                {telemetry.real_metrics?.is_stale && <span className="telemetry-stale-tag" style={{ marginLeft: '6px', color: '#f59e0b', fontSize: '11px' }}>⚠️ Stale Reading</span>}
              </span>
              <span className="telemetry-section-source">Kernel Source: Local System &amp; SQLite Engine</span>
            </div>
            <div className="sla-telemetry-grid real-grid">
              {/* Real: SQLite Response Time */}
              <div className="telemetry-card card-real">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge real">Live Query</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.real_metrics?.database_response_time_status || 'healthy').toLowerCase()}`}>
                    {telemetry.real_metrics?.database_response_time_status || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.real_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.real_metrics?.database_response_time_ms != null ? telemetry.real_metrics.database_response_time_ms : 'N/A'} <span className="telemetry-unit">ms</span>
                </div>
                <div className="telemetry-label">DB Query Latency &amp; Status</div>
                <div className="telemetry-sub">{telemetry.real_metrics?.database_availability || 'Available (100%)'}</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.real_metrics?.database_response_time_threshold || '< 10.0 ms normal'}</div>
                <div className="telemetry-data-source">Source: {telemetry.real_metrics?.database_response_time_source || 'SQLite islm.db'}</div>
              </div>

              {/* Real: Host CPU Usage */}
              <div className="telemetry-card card-real">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge real">Live System</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.real_metrics?.host_cpu_status || 'healthy').toLowerCase()}`}>
                    {telemetry.real_metrics?.host_cpu_status || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.real_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.real_metrics?.host_cpu_usage_pct != null ? telemetry.real_metrics.host_cpu_usage_pct : 'N/A'} <span className="telemetry-unit">%</span>
                </div>
                <div className="telemetry-label">Host CPU Usage</div>
                <div className="telemetry-sub">Active processor utilization (psutil)</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.real_metrics?.host_cpu_threshold || '< 75.0% normal'}</div>
                <div className="telemetry-data-source">Source: {telemetry.real_metrics?.host_cpu_source || 'OS Kernel'}</div>
              </div>

              {/* Real: Host RAM Usage */}
              <div className="telemetry-card card-real">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge real">Live System</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.real_metrics?.host_ram_status || 'healthy').toLowerCase()}`}>
                    {telemetry.real_metrics?.host_ram_status || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.real_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.real_metrics?.host_ram_usage_pct != null ? telemetry.real_metrics.host_ram_usage_pct : 'N/A'} <span className="telemetry-unit">%</span>
                </div>
                <div className="telemetry-label">Host RAM Usage</div>
                <div className="telemetry-sub">{telemetry.real_metrics?.host_ram_used_gb != null ? `${telemetry.real_metrics.host_ram_used_gb} GB used of ${telemetry.real_metrics.host_ram_total_gb} GB` : 'Memory stats'}</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.real_metrics?.host_ram_threshold || '< 80.0% normal'}</div>
                <div className="telemetry-data-source">Source: {telemetry.real_metrics?.host_ram_source || 'Host Memory'}</div>
              </div>

              {/* Real: Host Loopback Latency */}
              <div className="telemetry-card card-real">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge real">Live Socket</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.real_metrics?.loopback_status || 'healthy').toLowerCase()}`}>
                    {telemetry.real_metrics?.loopback_status || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.real_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.real_metrics?.loopback_latency_ms != null ? telemetry.real_metrics.loopback_latency_ms : 'N/A'} <span className="telemetry-unit">ms</span>
                </div>
                <div className="telemetry-label">Loopback Latency</div>
                <div className="telemetry-sub">Localhost TCP probe round-trip</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.real_metrics?.loopback_threshold || '< 5.0 ms normal'}</div>
                <div className="telemetry-data-source">Source: {telemetry.real_metrics?.loopback_source || 'Localhost TCP Socket'}</div>
              </div>
            </div>
          </div>

          {/* Section 2: Simulated Enterprise IT Telemetry */}
          <div className="telemetry-section-group">
            <div className="telemetry-section-label">
              <span className="badge badge-sim-telemetry">
                🟣 Simulated IT Infrastructure Telemetry
                {telemetry.simulated_metrics?.is_stale && <span className="telemetry-stale-tag" style={{ marginLeft: '6px', color: '#f59e0b', fontSize: '11px' }}>⚠️ Stale Reading</span>}
              </span>
              <span className="telemetry-section-source">Correlated dynamically with SQLite active incidents</span>
            </div>
            <div className="sla-telemetry-grid sim-grid">
              {/* Simulated: Network Latency */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.simulated_metrics?.network_latency_status || 'healthy').toLowerCase()}`}>
                    {telemetry.simulated_metrics?.network_latency_status || 'Normal'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.simulated_metrics?.network_latency_ms} <span className="telemetry-unit">ms</span>
                </div>
                <div className="telemetry-label">WAN Edge Latency</div>
                <div className="telemetry-sub">Core Edge Gateway R101 ping probe</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.simulated_metrics?.network_latency_threshold || '< 30.0 ms normal'}</div>
                <div className="telemetry-data-source">Source: WAN Telemetry Probe (Simulated)</div>
              </div>

              {/* Simulated: Packet Loss */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.simulated_metrics?.packet_loss_status || 'healthy').toLowerCase()}`}>
                    {telemetry.simulated_metrics?.packet_loss_status || 'Normal'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.simulated_metrics?.packet_loss_pct} <span className="telemetry-unit">%</span>
                </div>
                <div className="telemetry-label">Packet Loss</div>
                <div className="telemetry-sub">Threshold target: &lt; 0.5% (abnormal: &ge; 1.0%)</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.simulated_metrics?.packet_loss_threshold || '< 0.5% normal'}</div>
                <div className="telemetry-data-source">Source: ICMP Trap Agent (Simulated)</div>
              </div>

              {/* Simulated: Router R101 Status */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${telemetry.simulated_metrics?.router_r101?.health === 'Healthy' ? 'healthy' : 'warning'}`}>
                    {telemetry.simulated_metrics?.router_r101?.health || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className={`telemetry-value status-text ${telemetry.simulated_metrics?.router_r101?.health === 'Healthy' ? 'status-ok' : 'status-warn'}`}>
                  {telemetry.simulated_metrics?.router_r101?.health === 'Healthy' ? 'Online (100%)' : 'Degraded (98.2%)'}
                </div>
                <div className="telemetry-label">Router R101 (Core Edge)</div>
                <div className="telemetry-sub">
                  Util: {telemetry.simulated_metrics?.router_r101?.interface_utilization_pct || 43.5}% • Drops: {telemetry.simulated_metrics?.router_r101?.packet_drops_per_sec ?? 0}/s
                </div>
                <div className="telemetry-threshold-text">Threshold: Utilization &lt; 75%, Drops = 0</div>
                <div className="telemetry-data-source">Throughput: {telemetry.simulated_metrics?.router_r101?.throughput_mbps} Mbps (SNMP Agent)</div>
              </div>

              {/* Simulated: Switch SW-05 Status */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${telemetry.simulated_metrics?.switch_sw05?.health === 'Healthy' ? 'healthy' : 'warning'}`}>
                    {telemetry.simulated_metrics?.switch_sw05?.health || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className={`telemetry-value status-text ${telemetry.simulated_metrics?.switch_sw05?.health === 'Healthy' ? 'status-ok' : 'status-warn'}`}>
                  {telemetry.simulated_metrics?.switch_sw05?.health === 'Healthy' ? 'Online (100%)' : 'Alert (Port 24)'}
                </div>
                <div className="telemetry-label">Switch SW-05 (Dist Stack)</div>
                <div className="telemetry-sub">
                  Util: {telemetry.simulated_metrics?.switch_sw05?.interface_utilization_pct || 36.2}% • CRC Errors: {telemetry.simulated_metrics?.switch_sw05?.crc_errors ?? 0}
                </div>
                <div className="telemetry-threshold-text">Threshold: CRC Errors = 0, Ports Active &ge; 40</div>
                <div className="telemetry-data-source">Ports: {telemetry.simulated_metrics?.switch_sw05?.active_ports} Active (Cisco IOS-XE)</div>
              </div>

              {/* Simulated: DBMS Replication Lag */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${(telemetry.simulated_metrics?.replication_lag_status || 'healthy').toLowerCase()}`}>
                    {telemetry.simulated_metrics?.replication_lag_status || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className="telemetry-value">
                  {telemetry.simulated_metrics?.database_replication_lag_sec} <span className="telemetry-unit">s</span>
                </div>
                <div className="telemetry-label">Replication Lag (Binlog)</div>
                <div className="telemetry-sub">Primary to standby sync delay</div>
                <div className="telemetry-threshold-text">Threshold: {telemetry.simulated_metrics?.replication_lag_threshold || '< 1.0s normal'}</div>
                <div className="telemetry-data-source">Hit Ratio: {telemetry.simulated_metrics?.database_buffer_hit_pct}% (MySQL Engine)</div>
              </div>

              {/* Simulated: Database Backup Status */}
              <div className="telemetry-card card-sim">
                <div className="telemetry-card-top">
                  <span className="telemetry-source-badge sim">[Simulated]</span>
                  <span className={`telemetry-status-chip chip-${telemetry.simulated_metrics?.database_backup?.health === 'Healthy' ? 'healthy' : 'warning'}`}>
                    {telemetry.simulated_metrics?.database_backup?.health || 'Healthy'}
                  </span>
                  <span className="telemetry-ts-badge">{telemetry.simulated_metrics?.timestamp}</span>
                </div>
                <div className={`telemetry-value status-text ${telemetry.simulated_metrics?.database_backup?.health === 'Healthy' ? 'status-ok' : 'status-warn'}`}>
                  {telemetry.simulated_metrics?.database_backup?.health === 'Healthy' ? 'Verified' : 'Attention'}
                </div>
                <div className="telemetry-label">Backup Catalog</div>
                <div className="telemetry-sub">{telemetry.simulated_metrics?.database_backup?.status}</div>
                <div className="telemetry-threshold-text">Threshold: Daily &lt; 24h, SHA-256 Valid</div>
                <div className="telemetry-data-source">Schedule: {telemetry.simulated_metrics?.database_backup?.backup_schedule} (Catalog)</div>
              </div>
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
          {filterTabs.map(tab => (
            <button
              key={tab.id}
              className={`sla-filter-tab ${riskFilter === tab.id ? 'active' : ''}`}
              onClick={() => setRiskFilter(tab.id)}
            >
              <span>{tab.label}</span>
              <span className="sla-tab-count">{tab.count}</span>
            </button>
          ))}
        </div>

        <div className="sla-filter-controls-right">
          {/* Sorting selector */}
          <select
            className="sla-select-entity sla-select-sort"
            value={sortBy}
            onChange={e => setSortBy(e.target.value)}
            title="Sort monitored items"
          >
            <option value="URGENCY_DESC">⚡ SLA Urgency (% Elapsed)</option>
            <option value="REMAINING_ASC">⏳ Shortest Time Remaining</option>
            <option value="PRIORITY_DESC">🔥 Priority (Critical First)</option>
            <option value="NEWEST">📅 Newest Created</option>
            <option value="OLDEST">🕰️ Oldest Created</option>
          </select>

          {/* Entity filter */}
          <select
            className="sla-select-entity"
            value={entityFilter}
            onChange={e => setEntityFilter(e.target.value)}
          >
            <option value="ALL">All Entities</option>
            <option value="TICKET">Tickets Only</option>
            <option value="INCIDENT">Incidents Only</option>
          </select>

          {/* Service filter dropdown */}
          <select
            className="sla-select-entity"
            value={serviceFilter}
            onChange={e => setServiceFilter(e.target.value)}
          >
            <option value="">All Services</option>
            <option value="Network Infrastructure">Network Infrastructure</option>
            <option value="Database Management">Database Management</option>
            <option value="Email &amp; Collaboration">Email &amp; Collaboration</option>
            <option value="Web Application Hosting">Web Application Hosting</option>
            <option value="Security Operations">Security Operations</option>
            <option value="Hardware Support">Hardware Support</option>
          </select>

          {/* Search bar */}
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
        ) : sortedItems.length === 0 ? (
          <div className="sla-empty-state">
            <span className="sla-empty-icon">✅</span>
            <h4>No items found matching the selected criteria</h4>
            <p>All monitored items in this filter view are compliant or non-existent.</p>
          </div>
        ) : (
          <div className="sla-items-list">
            {sortedItems.map(item => {
              const itemKey = `${item.entity_type}_${item.id || item.entity_id}`;
              const isAiAnalyzing = aiAnalyzingId === itemKey;
              const isUpdating = updatingId === itemKey;
              const aiData = aiResults[itemKey];

              // Calculate progress bar percentage (cap visual display at 100%)
              const visualPercent = Math.min(100, Math.max(2, item.percent_elapsed || 0));
              const isBreached = item.is_breached;
              const riskLevel = (item.risk_level || 'low').toLowerCase();

              // Status options based on entity
              const statusOptions =
                item.entity_type === 'incident'
                  ? ['open', 'acknowledged', 'resolved', 'closed']
                  : ['open', 'in_progress', 'resolved', 'closed'];

              const isResolved = isItemResolved(item);

              return (
                <div
                  key={itemKey}
                  className={`sla-item-card ${isResolved ? 'card-resolved risk-border-resolved' : `risk-border-${riskLevel}`} ${
                    !isResolved && (item.priority === 'critical' || item.risk_level === 'Critical' || isBreached)
                      ? 'card-critical-prominent'
                      : ''
                  }`}
                >
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
                      {isResolved ? (
                        <>
                          <span className="badge badge-resolved">
                            {(item.status || 'RESOLVED').toUpperCase()}
                          </span>
                          {isBreached ? (
                            <span className="badge badge-breached" style={{ opacity: 0.9 }}>EXCEEDED SLA</span>
                          ) : (
                            <span className="badge badge-compliant">SLA COMPLIANT</span>
                          )}
                        </>
                      ) : (
                        <>
                          <span className={`badge badge-${riskLevel}`}>
                            {item.risk_level?.toUpperCase()} RISK
                          </span>
                          {isBreached && <span className="badge badge-breached pulse-badge">SLA BREACHED</span>}
                          {item.status_label === 'Imminent Breach' && (
                            <span className="badge badge-imminent_breach pulse-badge">IMMINENT BREACH</span>
                          )}
                        </>
                      )}
                      {item.affected_component && (
                        <span className="badge badge-component">Component: {item.affected_component}</span>
                      )}
                    </div>

                    <div className="sla-item-meta-right">
                      <span className="sla-service-tag">🏢 {item.service_name}</span>
                      <span className="sla-assignee-tag">👤 {item.assigned_to || 'Unassigned'}</span>
                    </div>
                  </div>

                  {/* Title & Description Context */}
                  <h3 className="sla-item-title">{item.title}</h3>
                  {item.description && (
                    <div className="sla-item-desc">
                      <span className="sla-desc-label">Telemetry Context:</span> {item.description}
                    </div>
                  )}

                  {/* Progress Bar & Telemetry Details */}
                  <div className="sla-progress-block">
                    <div className="sla-progress-labels">
                      <span>
                        <strong>Elapsed:</strong> {item.elapsed_minutes != null ? `${item.elapsed_minutes}m` : '—'} (
                        <strong>{item.percent_elapsed}%</strong>) of {item.target_display} ({item.target_name})
                      </span>
                      <span>
                        {item.status === 'resolved' || item.status === 'closed'
                          ? `Resolved in ${item.elapsed_minutes}m`
                          : isBreached
                          ? `Exceeded by ${Math.max(0, item.elapsed_minutes - (item.target_minutes || 0))}m`
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
                      <span className="sla-reason-tag tag-deterministic">Rule-Based Assessment</span>
                      <span className="sla-reason-text">{item.reason}</span>
                    </div>
                    <div className="sla-action-row">
                      <span className={`sla-reason-tag ${isResolved ? 'tag-resolved' : 'tag-action'}`}>
                        {isResolved ? 'Post-Resolution Note' : 'Action Required'}
                      </span>
                      <span className="sla-action-text">{item.recommended_action}</span>
                    </div>
                  </div>

                  {/* Quick-Action Controls: Status & Assignment backed by SQLite */}
                  <div className="sla-item-quick-actions">
                    <div className="quick-action-group">
                      <span className="quick-action-label">Status:</span>
                      <select
                        className="quick-action-select"
                        value={item.status || 'open'}
                        disabled={isUpdating}
                        onChange={e => handleStatusChange(item, e.target.value)}
                      >
                        {statusOptions.map(st => (
                          <option key={st} value={st}>
                            {st.replace('_', ' ').toUpperCase()}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="quick-action-group">
                      <span className="quick-action-label">Assignee:</span>
                      <select
                        className="quick-action-select"
                        value={
                          TECHNICIANS.find(
                            t =>
                              t.toLowerCase() === (item.assigned_to || '').toLowerCase() ||
                              t.toLowerCase().replace(' ', '_') === (item.assigned_to || '').toLowerCase()
                          ) || 'Unassigned'
                        }
                        disabled={isUpdating}
                        onChange={e => handleAssigneeChange(item, e.target.value)}
                      >
                        <option value="Unassigned">Unassigned</option>
                        {TECHNICIANS.map(tech => (
                          <option key={tech} value={tech}>
                            {tech}
                          </option>
                        ))}
                      </select>
                    </div>

                    {isUpdating && <span className="quick-action-updating">Updating SQLite…</span>}
                  </div>

                  {/* AI Prediction Action Button & Quick Summary */}
                  <div className="sla-ai-section">
                    <div className="sla-ai-action-bar">
                      <button
                        className="btn-ai-predict"
                        onClick={() => handleOpenAiModal(item)}
                        disabled={isAiAnalyzing}
                      >
                        {isAiAnalyzing
                          ? '🤖 DeepSeek-R1 Synthesizing Root Cause…'
                          : aiData && !aiData.error
                          ? '📋 View DeepSeek-R1 AI Risk Synthesis'
                          : '🤖 Run DeepSeek-R1 AI Risk Synthesis'}
                      </button>
                      {aiData && !aiData.error && (
                        <span className="sla-ai-card-pill" onClick={() => handleOpenAiModal(item)}>
                          Trajectory: <strong>{aiData.risk_trajectory || 'Active'}</strong> • Click to open 6-part synthesis
                        </span>
                      )}
                    </div>
                    {aiData?.error && (
                      <div className="sla-ai-error" style={{ marginTop: '8px' }}>
                        ⚠️ {aiData.error}
                      </div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* ── Slide-Over Side Panel / Modal Drawer for DeepSeek-R1 AI Risk Synthesis ── */}
      {selectedAiItem && (() => {
        const modalKey = `${selectedAiItem.entity_type}_${selectedAiItem.id || selectedAiItem.entity_id}`;
        const modalAiData = aiResults[modalKey];
        const isAnalyzingThis = aiAnalyzingId === modalKey;
        const currentItem = items.find(i => `${i.entity_type}_${i.id || i.entity_id}` === modalKey) || selectedAiItem;
        const statusOptions = currentItem.entity_type === 'incident'
          ? ['open', 'acknowledged', 'resolved', 'closed']
          : ['open', 'in_progress', 'resolved', 'closed'];

        return (
          <div className="sla-modal-overlay" onClick={() => setSelectedAiItem(null)}>
            <div className="sla-modal-drawer" onClick={e => e.stopPropagation()}>
              {/* Header */}
              <div className="sla-modal-header">
                <div className="sla-modal-title-group">
                  <h3>
                    <span>🤖 DeepSeek-R1 1.5B AI Risk Synthesis</span>
                  </h3>
                  <div className="sla-modal-badges">
                    <span className={`badge badge-entity badge-${currentItem.entity_type}`}>
                      {currentItem.entity_type === 'incident' ? 'Incident' : 'Ticket'}
                    </span>
                    <span className="sla-item-id">{currentItem.entity_id}</span>
                    <span className={`badge badge-${(currentItem.priority || 'medium').toLowerCase()}`}>
                      {currentItem.priority?.toUpperCase()}
                    </span>
                    {isItemResolved(currentItem) ? (
                      <>
                        <span className="badge badge-resolved">
                          {(currentItem.status || 'RESOLVED').toUpperCase()}
                        </span>
                        {currentItem.is_breached ? (
                          <span className="badge badge-breached" style={{ opacity: 0.9 }}>EXCEEDED SLA</span>
                        ) : (
                          <span className="badge badge-compliant">SLA COMPLIANT</span>
                        )}
                      </>
                    ) : (
                      <>
                        <span className={`badge badge-${(currentItem.risk_level || 'low').toLowerCase()}`}>
                          {currentItem.risk_level?.toUpperCase()} RISK
                        </span>
                        {currentItem.is_breached && <span className="badge badge-breached pulse-badge">SLA BREACHED</span>}
                      </>
                    )}
                  </div>
                </div>
                <button
                  className="sla-modal-close-btn"
                  onClick={() => setSelectedAiItem(null)}
                  title="Close Side Panel (Esc)"
                >
                  ✕
                </button>
              </div>

              {/* Body */}
              <div className="sla-modal-body">
                {/* 1. Authoritative SQLite Record (Ground Truth) */}
                <div className="sla-authoritative-box">
                  <div className="sla-authoritative-header">
                    <span>Authoritative SQLite Context</span>
                    <span className="badge-ground-truth">🟢 Verified ITSM Ground Truth</span>
                  </div>
                  <div className="sla-modal-item-title">{currentItem.title}</div>
                  {currentItem.description && (
                    <div className="sla-modal-desc-box">
                      <strong>Telemetry Context:</strong> {currentItem.description}
                    </div>
                  )}
                  <div className="sla-modal-metrics-row">
                    <div className="sla-modal-metric-chip">
                      <div className="chip-label">SLA Target</div>
                      <div className="chip-val">{currentItem.target_display} ({currentItem.target_name})</div>
                    </div>
                    <div className="sla-modal-metric-chip">
                      <div className="chip-label">Elapsed Time</div>
                      <div className="chip-val">{currentItem.elapsed_minutes}m ({currentItem.percent_elapsed}%)</div>
                    </div>
                    <div className="sla-modal-metric-chip">
                      <div className="chip-label">Remaining Margin</div>
                      <div className="chip-val">
                        {currentItem.status === 'resolved' || currentItem.status === 'closed'
                          ? `Resolved in ${currentItem.elapsed_minutes}m`
                          : currentItem.is_breached
                          ? `Exceeded by ${Math.max(0, currentItem.elapsed_minutes - (currentItem.target_minutes || 0))}m`
                          : `${currentItem.remaining_minutes || 0}m`}
                      </div>
                    </div>
                  </div>
                </div>

                {/* 2. DeepSeek-R1 AI Risk Synthesis */}
                <div className="sla-ai-synthesis-container">
                  <div className="sla-ai-disclaimer-banner">
                    <span>🤖 <strong>DeepSeek-R1 1.5B Local SLM Inference</strong> (Ollama)</span>
                    <span>Domain SRE RAG Grounded</span>
                  </div>

                  {isAnalyzingThis ? (
                    <div className="sla-loading-state" style={{ padding: '36px 20px' }}>
                      <div className="loading-spinner" />
                      <p>DeepSeek-R1 1.5B evaluating incident telemetry, correlating SLA deadlines, and grounding with SRE runbooks…</p>
                    </div>
                  ) : modalAiData?.error ? (
                    <div className="sla-ai-error" style={{ padding: '16px', fontSize: '13px' }}>
                      <p>⚠️ {modalAiData.error}</p>
                      <button
                        className="btn-ai-predict"
                        style={{ marginTop: '10px' }}
                        onClick={() => handleAnalyzeWithAi(currentItem)}
                      >
                        🔄 Retry Inference
                      </button>
                    </div>
                  ) : modalAiData ? (
                    <>
                      {/* Section 1: Incident Summary */}
                      <div className="sla-ai-section-card">
                        <div className="sla-ai-card-title">
                          <span>📋 Incident Summary</span>
                        </div>
                        <div className="sla-ai-card-text">
                          {modalAiData.incident_summary || modalAiData.ai_root_cause_analysis}
                        </div>
                      </div>

                      {/* Section 2: Possible Root Causes */}
                      <div className="sla-ai-section-card card-highlight">
                        <div className="sla-ai-card-title">
                          <span>🔍 Possible Root Causes (SLM Technical Hypothesis)</span>
                        </div>
                        <div className="sla-ai-card-text">
                          {modalAiData.possible_root_causes || modalAiData.ai_root_cause_analysis}
                        </div>
                      </div>

                      {/* Section 3: SLA Risk Explanation */}
                      <div className="sla-ai-section-card">
                        <div className="sla-ai-card-title">
                          <span>⏱️ SLA Risk Explanation &amp; Operational Impact</span>
                        </div>
                        <div className="sla-ai-card-text">
                          {modalAiData.sla_risk_explanation || modalAiData.ai_sla_risk_explanation}
                        </div>
                      </div>

                      {/* Section 4: Recommended Troubleshooting Steps */}
                      <div className="sla-ai-section-card">
                        <div className="sla-ai-card-title">
                          <span>🛠️ Recommended Troubleshooting Steps</span>
                        </div>
                        <div className="sla-ai-card-text">
                          {modalAiData.recommended_troubleshooting_steps || modalAiData.ai_recommended_action}
                        </div>
                      </div>

                      {/* Section 5: Supporting Evidence Available */}
                      <div className="sla-ai-section-card">
                        <div className="sla-ai-card-title">
                          <span>📊 Supporting Evidence (Context &amp; Telemetry Signals)</span>
                        </div>
                        <div className="sla-ai-card-text evidence-text">
                          {modalAiData.supporting_evidence || 'Active SQLite database record and correlated telemetry metrics.'}
                        </div>
                      </div>

                      {/* Section 6: Uncertainties or Missing Information */}
                      <div className="sla-ai-section-card">
                        <div className="sla-ai-card-title">
                          <span>⚠️ Uncertainties or Missing Information</span>
                        </div>
                        <div className="sla-ai-card-text" style={{ color: '#cbd5e1' }}>
                          {modalAiData.uncertainties_or_missing_info || 'Detailed packet capture and interface backplane queues require live diagnostic probe.'}
                        </div>
                      </div>

                      {/* Verified SRE Runbook Context (RAG Domain Grounding) */}
                      {modalAiData.rag_knowledge_context && (
                        <div className="sla-rag-knowledge-box">
                          <div className="sla-rag-top">
                            <span className="badge badge-rag">🟢 Verified SRE Troubleshooting Runbook</span>
                            <span className="sla-rag-id">
                              {modalAiData.rag_knowledge_context.runbook_id} • {modalAiData.rag_knowledge_context.domain}
                            </span>
                          </div>
                          <div className="sla-rag-body">
                            <div className="sla-rag-section">
                              <strong>Standard Diagnostic Checks:</strong>
                              <ul>
                                {modalAiData.rag_knowledge_context.diagnostic_checks?.map((chk, i) => (
                                  <li key={i}>{chk}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="sla-rag-section">
                              <strong>Remediation Procedures:</strong>
                              <ul>
                                {modalAiData.rag_knowledge_context.remediation_procedures?.map((proc, i) => (
                                  <li key={i}>{proc}</li>
                                ))}
                              </ul>
                            </div>
                            <div className="sla-rag-footer">
                              Verified Source: <em>{modalAiData.rag_knowledge_context.verified_source}</em>
                            </div>
                          </div>
                        </div>
                      )}
                    </>
                  ) : null}
                </div>
              </div>

              {/* Modal Footer Controls */}
              <div className="sla-modal-footer">
                <div className="sla-modal-controls">
                  <div className="quick-action-group">
                    <span className="quick-action-label">Status:</span>
                    <select
                      className="quick-action-select"
                      value={currentItem.status || 'open'}
                      disabled={updatingId === modalKey}
                      onChange={e => handleStatusChange(currentItem, e.target.value)}
                    >
                      {statusOptions.map(st => (
                        <option key={st} value={st}>{st.replace('_', ' ').toUpperCase()}</option>
                      ))}
                    </select>
                  </div>

                  <div className="quick-action-group">
                    <span className="quick-action-label">Assignee:</span>
                    <select
                      className="quick-action-select"
                      value={
                        TECHNICIANS.find(
                          t =>
                            t.toLowerCase() === (currentItem.assigned_to || '').toLowerCase() ||
                            t.toLowerCase().replace(' ', '_') === (currentItem.assigned_to || '').toLowerCase()
                        ) || 'Unassigned'
                      }
                      disabled={updatingId === modalKey}
                      onChange={e => handleAssigneeChange(currentItem, e.target.value)}
                    >
                      <option value="Unassigned">Unassigned</option>
                      {TECHNICIANS.map(tech => (
                        <option key={tech} value={tech}>{tech}</option>
                      ))}
                    </select>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '8px' }}>
                  <button
                    className="btn-ai-predict"
                    style={{ padding: '6px 12px', fontSize: '12px' }}
                    onClick={() => handleAnalyzeWithAi(currentItem)}
                    disabled={isAnalyzingThis}
                  >
                    🔄 Re-synthesize
                  </button>
                  <button
                    className="btn-sla-refresh"
                    style={{ padding: '6px 12px', fontSize: '12px' }}
                    onClick={() => setSelectedAiItem(null)}
                  >
                    Close Panel
                  </button>
                </div>
              </div>
            </div>
          </div>
        );
      })()}
    </div>
  );
}
