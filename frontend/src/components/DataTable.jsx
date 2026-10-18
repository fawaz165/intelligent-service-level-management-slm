/**
 * DataTable — renders structured query results in a styled table.
 *
 * Adapts columns and formatting based on data_type (tickets, services, files, users, sla).
 */

const COLUMN_CONFIG = {
  tickets: [
    { key: 'id', label: 'ID' },
    { key: 'title', label: 'Title', truncate: 40 },
    { key: 'category', label: 'Category' },
    { key: 'priority', label: 'Priority', badge: true },
    { key: 'status', label: 'Status', badge: true },
    { key: 'assignee_name', label: 'Assigned To' },
  ],
  services: [
    { key: 'id', label: 'ID' },
    { key: 'service_name', label: 'Service Name' },
    { key: 'status', label: 'Status', badge: true },
    { key: 'owner', label: 'Owner' },
  ],
  files: [
    { key: 'id', label: 'ID' },
    { key: 'file_name', label: 'File Name' },
    { key: 'file_type', label: 'Type' },
    { key: 'file_size_display', label: 'Size' },
    { key: 'uploader_name', label: 'Uploaded By' },
  ],
  users: [
    { key: 'id', label: 'ID' },
    { key: 'name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'role', label: 'Role' },
  ],
  sla: [
    { key: 'id', label: 'ID' },
    { key: 'service_name', label: 'Service' },
    { key: 'priority', label: 'Priority', badge: true },
    { key: 'response_time', label: 'Response Time' },
    { key: 'resolution_time', label: 'Resolution Time' },
  ],
  incidents: [
    { key: 'incident_id', label: 'Incident ID' },
    { key: 'title', label: 'Title', truncate: 35 },
    { key: 'severity', label: 'Severity', badge: true },
    { key: 'affected_service', label: 'Affected Service' },
    { key: 'status', label: 'Status', badge: true },
    { key: 'assigned_to', label: 'Assigned To' },
  ],
  sla_risks: [
    { key: 'entity_id', label: 'Item ID' },
    { key: 'title', label: 'Title', isTitle: true },
    { key: 'service_name', label: 'Service' },
    { key: 'priority', label: 'Priority', badge: true },
    { key: 'risk_level', label: 'Risk Level', badge: true },
    { key: 'percent_elapsed', label: 'SLA Elapsed', formatPercent: true },
    { key: 'status_label', label: 'SLA Status', badge: true },
    { key: 'recommended_action', label: 'Recommended Action', isAction: true },
  ],
};

function truncate(text, max) {
  if (!text || text.length <= max) return text;
  return text.slice(0, max) + '…';
}

export default function DataTable({ data, dataType }) {
  if (!data || data.length === 0) return null;

  const columns = COLUMN_CONFIG[dataType] || Object.keys(data[0]).map(k => ({ key: k, label: k }));

  return (
    <div className="data-table-wrapper">
      <table className="data-table">
        <thead>
          <tr>
            {columns.map(col => (
              <th
                key={col.key}
                className={`col-${col.key} ${col.isAction ? 'col-action' : ''} ${col.isTitle ? 'col-title' : ''}`}
              >
                {col.label}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.map((row, i) => (
            <tr key={row.entity_id || row.incident_id || row.id || i}>
              {columns.map(col => (
                <td
                  key={col.key}
                  className={`col-${col.key} ${col.isAction ? 'col-action' : ''} ${col.isTitle ? 'col-title' : ''}`}
                >
                  {col.badge ? (
                    <span className={`badge badge-${(row[col.key] || '').toLowerCase().replace(/[\s\-_]+/g, '_')}`}>
                      {row[col.key] || '—'}
                    </span>
                  ) : col.formatPercent ? (
                    <span className="sla-percent-value">
                      {row[col.key] != null ? `${row[col.key]}%` : '—'}
                    </span>
                  ) : col.isAction ? (
                    <div className="action-text-wrapper" title={row[col.key] || ''}>
                      {row[col.key] || '—'}
                    </div>
                  ) : col.isTitle ? (
                    <div className="title-text-wrapper" title={row[col.key] || ''}>
                      {row[col.key] || '—'}
                    </div>
                  ) : col.truncate ? (
                    truncate(row[col.key], col.truncate) || '—'
                  ) : (
                    row[col.key] ?? '—'
                  )}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
