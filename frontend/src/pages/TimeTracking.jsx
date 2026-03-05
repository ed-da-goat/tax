import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import useAuth from '../hooks/useAuth';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatCurrency, formatDate } from '../utils/format';

const STATUS_COLORS = {
  DRAFT: '#6B7280', SUBMITTED: '#3B82F6', APPROVED: '#10B981', BILLED: '#8B5CF6',
};

export default function TimeTracking() {
  const { user } = useAuth();
  const [showAdd, setShowAdd] = useState(false);
  const [toast, setToast] = useState(null);
  const [selected, setSelected] = useState([]);
  const [filters, setFilters] = useState({ status: '', client_id: '' });

  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.client_id) params.set('client_id', filters.client_id);

  const { data, refetch } = useApiQuery(['time-entries', filters], `/api/v1/time-entries?${params}`);
  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const { data: activeTimer } = useApiQuery(['active-timer'], '/api/v1/timers/active');

  const addEntry = useApiMutation('post', '/api/v1/time-entries', { invalidate: [['time-entries']] });
  const submitEntries = useApiMutation('post', '/api/v1/time-entries/submit', { invalidate: [['time-entries']] });
  const approveEntries = useApiMutation('post', '/api/v1/time-entries/approve', { invalidate: [['time-entries']] });
  const startTimer = useApiMutation('post', '/api/v1/timers', { invalidate: [['active-timer']] });
  const stopTimer = useApiMutation('post', (body) => `/api/v1/timers/${body.id}/stop`, { invalidate: [['active-timer']] });
  const convertTimer = useApiMutation('post', (body) => `/api/v1/timers/${body.id}/convert`, { invalidate: [['active-timer'], ['time-entries']] });

  const [form, setForm] = useState({ client_id: '', entry_date: '', duration_minutes: '', description: '', is_billable: true, service_type: '' });

  async function handleAdd(e) {
    e.preventDefault();
    try {
      await addEntry.mutateAsync({ ...form, duration_minutes: parseInt(form.duration_minutes) });
      setShowAdd(false);
      setForm({ client_id: '', entry_date: '', duration_minutes: '', description: '', is_billable: true, service_type: '' });
      setToast({ type: 'success', message: 'Time entry created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handleSubmit() {
    try {
      await submitEntries.mutateAsync(selected);
      setSelected([]);
      setToast({ type: 'success', message: 'Entries submitted for approval' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handleApprove() {
    try {
      await approveEntries.mutateAsync(selected);
      setSelected([]);
      setToast({ type: 'success', message: 'Entries approved' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handleStartTimer() {
    try {
      await startTimer.mutateAsync({ description: 'Working...' });
      setToast({ type: 'success', message: 'Timer started' });
    } catch (err) { setToast({ type: 'error', message: 'Failed to start timer' }); }
  }

  async function handleStopTimer() {
    if (!activeTimer) return;
    try {
      await stopTimer.mutateAsync({ id: activeTimer.id });
      await convertTimer.mutateAsync({ id: activeTimer.id });
      setToast({ type: 'success', message: 'Timer stopped and converted to entry' });
    } catch (err) { setToast({ type: 'error', message: 'Failed' }); }
  }

  const entries = data?.items || [];
  const clientList = clients?.items || [];

  const columns = [
    { key: 'select', label: '', render: (row) => (
      <input type="checkbox" checked={selected.includes(row.id)} onChange={(e) => {
        setSelected(e.target.checked ? [...selected, row.id] : selected.filter(id => id !== row.id));
      }} />
    )},
    { key: 'entry_date', label: 'Date', render: (row) => formatDate(row.entry_date) },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'duration', label: 'Duration', render: (row) => `${Math.floor(row.duration_minutes / 60)}h ${row.duration_minutes % 60}m` },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    { key: 'service_type', label: 'Service', render: (row) => row.service_type || '—' },
    { key: 'amount', label: 'Amount', render: (row) => row.amount ? formatCurrency(row.amount) : '—' },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Time Tracking</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          {activeTimer ? (
            <button className="btn btn--danger" onClick={handleStopTimer}>Stop Timer</button>
          ) : (
            <button className="btn btn--outline" onClick={handleStartTimer}>Start Timer</button>
          )}
          <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ Add Entry</button>
          {selected.length > 0 && (
            <>
              <button className="btn btn--outline" onClick={handleSubmit}>Submit ({selected.length})</button>
              {user?.role === 'CPA_OWNER' && (
                <button className="btn btn--success" onClick={handleApprove}>Approve ({selected.length})</button>
              )}
            </>
          )}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          <option value="DRAFT">Draft</option>
          <option value="SUBMITTED">Submitted</option>
          <option value="APPROVED">Approved</option>
          <option value="BILLED">Billed</option>
        </select>
        <select value={filters.client_id} onChange={e => setFilters(f => ({ ...f, client_id: e.target.value }))}>
          <option value="">All Clients</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <DataTable columns={columns} rows={entries} emptyMessage="No time entries found" />

      {showAdd && (
        <Modal title="Add Time Entry" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleAdd}>
            <FormField label="Client" required>
              <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                <option value="">Select client...</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <FormField label="Date" required>
              <input type="date" value={form.entry_date} onChange={e => setForm(f => ({ ...f, entry_date: e.target.value }))} required />
            </FormField>
            <FormField label="Duration (minutes)" required>
              <input type="number" min="1" value={form.duration_minutes} onChange={e => setForm(f => ({ ...f, duration_minutes: e.target.value }))} required />
            </FormField>
            <FormField label="Description">
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </FormField>
            <FormField label="Service Type">
              <select value={form.service_type} onChange={e => setForm(f => ({ ...f, service_type: e.target.value }))}>
                <option value="">Select...</option>
                <option value="Tax Preparation">Tax Preparation</option>
                <option value="Bookkeeping">Bookkeeping</option>
                <option value="Payroll Processing">Payroll Processing</option>
                <option value="Advisory">Advisory</option>
                <option value="Audit & Assurance">Audit & Assurance</option>
              </select>
            </FormField>
            <FormField label="Billable">
              <input type="checkbox" checked={form.is_billable} onChange={e => setForm(f => ({ ...f, is_billable: e.target.checked }))} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={addEntry.isPending}>Save</button>
            </div>
          </form>
        </Modal>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
