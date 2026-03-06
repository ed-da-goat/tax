import { useState } from 'react';
import useApi from '../hooks/useApi';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import { formatDate } from '../utils/format';

const TABLE_OPTIONS = [
  { value: '', label: 'All Tables' },
  { value: 'clients', label: 'clients' },
  { value: 'journal_entries', label: 'journal_entries' },
  { value: 'invoices', label: 'invoices' },
  { value: 'bills', label: 'bills' },
  { value: 'payroll_runs', label: 'payroll_runs' },
  { value: 'employees', label: 'employees' },
];

const ACTION_OPTIONS = [
  { value: '', label: 'All Actions' },
  { value: 'INSERT', label: 'INSERT' },
  { value: 'UPDATE', label: 'UPDATE' },
  { value: 'DELETE', label: 'DELETE' },
];

const ACTION_COLORS = {
  INSERT: '#10B981',
  UPDATE: '#3d6d8e',
  DELETE: '#EF4444',
};

const PAGE_SIZE = 50;

function truncateId(id) {
  if (!id) return '--';
  const str = String(id);
  return str.length > 12 ? str.slice(0, 12) + '...' : str;
}

function formatTimestamp(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  });
}

function JsonDiff({ label, data, color }) {
  if (!data || Object.keys(data).length === 0) return null;
  return (
    <div style={{ marginBottom: 12 }}>
      <div style={{ fontWeight: 600, marginBottom: 4, color }}>{label}</div>
      <pre
        style={{
          backgroundColor: color === '#EF4444' ? '#FEF2F2' : '#F0FDF4',
          border: `1px solid ${color === '#EF4444' ? '#FECACA' : '#BBF7D0'}`,
          borderRadius: 6,
          padding: 12,
          fontSize: 13,
          overflow: 'auto',
          maxHeight: 300,
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

export default function AuditTrail() {
  const api = useApi();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Filters
  const [tableName, setTableName] = useState('');
  const [action, setAction] = useState('');
  const [userId, setUserId] = useState('');
  const [dateFrom, setDateFrom] = useState('');
  const [dateTo, setDateTo] = useState('');

  // Data
  const [entries, setEntries] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);

  // Detail modal
  const [selected, setSelected] = useState(null);

  const fetchAuditLog = async (pageNum = 0) => {
    setLoading(true);
    setError('');
    try {
      const params = { skip: pageNum * PAGE_SIZE, limit: PAGE_SIZE };
      if (tableName) params.table_name = tableName;
      if (action) params.action = action;
      if (userId) params.user_id = userId;
      if (dateFrom) params.date_from = dateFrom;
      if (dateTo) params.date_to = dateTo;

      const res = await api.get('/api/v1/audit-log', { params });
      setEntries(res.data.items || []);
      setTotal(res.data.total || 0);
      setPage(pageNum);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to load audit log');
    }
    setLoading(false);
  };

  const handleSearch = () => {
    fetchAuditLog(0);
  };

  const handlePageChange = (newPage) => {
    fetchAuditLog(newPage);
  };

  const handleRowClick = async (row) => {
    try {
      const res = await api.get(`/api/v1/audit-log/${row.id}`);
      setSelected(res.data);
    } catch {
      setSelected(row);
    }
  };

  const columns = [
    {
      key: 'created_at',
      label: 'Timestamp',
      render: (val) => formatTimestamp(val),
    },
    {
      key: 'table_name',
      label: 'Table',
    },
    {
      key: 'action',
      label: 'Action',
      render: (val) => (
        <span
          className="badge"
          style={{ backgroundColor: ACTION_COLORS[val] || '#6B7280' }}
        >
          {val}
        </span>
      ),
    },
    {
      key: 'record_id',
      label: 'Record ID',
      render: (val) => (
        <span title={val} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {truncateId(val)}
        </span>
      ),
    },
    {
      key: 'user_id',
      label: 'User ID',
      render: (val) => (
        <span title={val} style={{ fontFamily: 'monospace', fontSize: 12 }}>
          {truncateId(val)}
        </span>
      ),
    },
  ];

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      <div className="page-header">
        <h1 className="page-title">Audit Trail</h1>
      </div>

      {/* Filters */}
      <div className="card" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'flex-end' }}>
          <FormField label="Table">
            <select
              className="form-input form-select"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
            >
              {TABLE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </FormField>
          <FormField label="Action">
            <select
              className="form-input form-select"
              value={action}
              onChange={(e) => setAction(e.target.value)}
            >
              {ACTION_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>{opt.label}</option>
              ))}
            </select>
          </FormField>
          <FormField label="User ID">
            <input
              className="form-input"
              type="text"
              placeholder="Filter by user..."
              value={userId}
              onChange={(e) => setUserId(e.target.value)}
            />
          </FormField>
          <FormField label="Date From">
            <input
              className="form-input"
              type="date"
              value={dateFrom}
              onChange={(e) => setDateFrom(e.target.value)}
            />
          </FormField>
          <FormField label="Date To">
            <input
              className="form-input"
              type="date"
              value={dateTo}
              onChange={(e) => setDateTo(e.target.value)}
            />
          </FormField>
          <button
            className={`btn btn--primary${loading ? ' btn--loading' : ''}`}
            onClick={handleSearch}
            disabled={loading}
            style={{ marginBottom: 16 }}
          >
            Search
          </button>
        </div>
      </div>

      {error && <div className="alert alert--error" style={{ marginBottom: 16 }}>{error}</div>}

      {entries.length === 0 && !loading && total === 0 && (
        <div className="empty-state">
          <div className="empty-state-heading">No audit log entries</div>
          <div className="empty-state-text">Use the filters above and click Search to load the audit trail.</div>
        </div>
      )}

      {(entries.length > 0 || loading) && (
        <DataTable
          columns={columns}
          data={entries}
          total={total}
          page={page}
          pageSize={PAGE_SIZE}
          onPageChange={handlePageChange}
          loading={loading}
          emptyMessage="No entries match your filters."
          onRowClick={handleRowClick}
        />
      )}

      {/* Detail Modal */}
      <Modal isOpen={!!selected} title="Audit Log Entry" onClose={() => setSelected(null)} size="lg">
        {selected && (
          <div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>Timestamp</div>
                <div style={{ fontWeight: 600 }}>{formatTimestamp(selected.created_at)}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>Action</div>
                <span className="badge" style={{ backgroundColor: ACTION_COLORS[selected.action] || '#6B7280' }}>
                  {selected.action}
                </span>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>Table</div>
                <div style={{ fontWeight: 600 }}>{selected.table_name}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>Record ID</div>
                <div style={{ fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all' }}>{selected.record_id}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>User ID</div>
                <div style={{ fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all' }}>{selected.user_id}</div>
              </div>
              <div>
                <div style={{ fontSize: 12, color: '#6B7280', marginBottom: 2 }}>Entry ID</div>
                <div style={{ fontFamily: 'monospace', fontSize: 13, wordBreak: 'break-all' }}>{selected.id}</div>
              </div>
            </div>

            <JsonDiff label="Old Values" data={selected.old_values} color="#EF4444" />
            <JsonDiff label="New Values" data={selected.new_values} color="#10B981" />
          </div>
        )}
      </Modal>
    </div>
  );
}
