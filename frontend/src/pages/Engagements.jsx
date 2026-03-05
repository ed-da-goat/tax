import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatCurrency, formatDate } from '../utils/format';

const STATUS_COLORS = {
  DRAFT: '#6B7280', SENT: '#3B82F6', VIEWED: '#8B5CF6',
  SIGNED: '#10B981', DECLINED: '#EF4444', EXPIRED: '#9CA3AF',
};

const ENGAGEMENT_TYPES = ['Tax Preparation', 'Bookkeeping', 'Payroll', 'Advisory', 'Audit', 'Compilation', 'Review'];
const FEE_TYPES = ['FIXED', 'HOURLY', 'RETAINER'];

export default function Engagements() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [filters, setFilters] = useState({ status: '', client_id: '' });

  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.client_id) params.set('client_id', filters.client_id);

  const { data } = useApiQuery(['engagements', filters], `/api/v1/engagements?${params}`);
  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');

  const createEng = useApiMutation('post', '/api/v1/engagements', { invalidate: [['engagements']] });
  const sendEng = useApiMutation('post', (body) => `/api/v1/engagements/${body.id}/send`, { invalidate: [['engagements']] });
  const deleteEng = useApiMutation('delete', (body) => `/api/v1/engagements/${body.id}`, { invalidate: [['engagements']] });

  const [form, setForm] = useState({
    client_id: '', title: '', engagement_type: 'Tax Preparation', description: '',
    terms_and_conditions: '', fee_type: 'FIXED', fixed_fee: '', hourly_rate: '',
    estimated_hours: '', retainer_amount: '', start_date: '', end_date: '', tax_year: '',
  });

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        fixed_fee: form.fixed_fee ? parseFloat(form.fixed_fee) : null,
        hourly_rate: form.hourly_rate ? parseFloat(form.hourly_rate) : null,
        estimated_hours: form.estimated_hours ? parseFloat(form.estimated_hours) : null,
        retainer_amount: form.retainer_amount ? parseFloat(form.retainer_amount) : null,
        tax_year: form.tax_year ? parseInt(form.tax_year) : null,
        start_date: form.start_date || null,
        end_date: form.end_date || null,
        terms_and_conditions: form.terms_and_conditions || null,
        description: form.description || null,
      };
      await createEng.mutateAsync(payload);
      setShowAdd(false);
      setToast({ type: 'success', message: 'Engagement created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  const items = data?.items || [];
  const clientList = clients?.items || [];

  const columns = [
    { key: 'title', label: 'Title' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'engagement_type', label: 'Type' },
    { key: 'fee', label: 'Fee', render: (row) => {
      if (row.fee_type === 'FIXED') return formatCurrency(row.fixed_fee || 0);
      if (row.fee_type === 'HOURLY') return `${formatCurrency(row.hourly_rate || 0)}/hr`;
      if (row.fee_type === 'RETAINER') return `${formatCurrency(row.retainer_amount || 0)}/mo`;
      return '—';
    }},
    { key: 'tax_year', label: 'Tax Year', render: (row) => row.tax_year || '—' },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
    { key: 'actions', label: 'Actions', render: (row) => (
      <div style={{ display: 'flex', gap: '4px' }}>
        {row.status === 'DRAFT' && <button className="btn btn--small btn--primary" onClick={() => sendEng.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Sent' }))}>Send</button>}
        {row.status === 'DRAFT' && <button className="btn btn--small btn--danger" onClick={() => deleteEng.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Deleted' }))}>Delete</button>}
      </div>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Engagement Letters</h1>
        <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ New Engagement</button>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All Statuses</option>
          {Object.keys(STATUS_COLORS).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filters.client_id} onChange={e => setFilters(f => ({ ...f, client_id: e.target.value }))}>
          <option value="">All Clients</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <DataTable columns={columns} rows={items} emptyMessage="No engagement letters" />

      {showAdd && (
        <Modal title="New Engagement Letter" onClose={() => setShowAdd(false)} wide>
          <form onSubmit={handleCreate}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <FormField label="Client" required>
                <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">Select...</option>
                  {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </FormField>
              <FormField label="Type" required>
                <select value={form.engagement_type} onChange={e => setForm(f => ({ ...f, engagement_type: e.target.value }))}>
                  {ENGAGEMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </FormField>
              <FormField label="Title" required>
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} required />
              </FormField>
              <FormField label="Tax Year">
                <input type="number" value={form.tax_year} onChange={e => setForm(f => ({ ...f, tax_year: e.target.value }))} placeholder="2026" />
              </FormField>
              <FormField label="Start Date">
                <input type="date" value={form.start_date} onChange={e => setForm(f => ({ ...f, start_date: e.target.value }))} />
              </FormField>
              <FormField label="End Date">
                <input type="date" value={form.end_date} onChange={e => setForm(f => ({ ...f, end_date: e.target.value }))} />
              </FormField>
            </div>
            <FormField label="Description">
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} />
            </FormField>
            <h3 style={{ marginTop: '16px' }}>Fee Structure</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <FormField label="Fee Type">
                <select value={form.fee_type} onChange={e => setForm(f => ({ ...f, fee_type: e.target.value }))}>
                  {FEE_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </FormField>
              {form.fee_type === 'FIXED' && (
                <FormField label="Fixed Fee">
                  <input type="number" step="0.01" min="0" value={form.fixed_fee} onChange={e => setForm(f => ({ ...f, fixed_fee: e.target.value }))} />
                </FormField>
              )}
              {form.fee_type === 'HOURLY' && (
                <>
                  <FormField label="Hourly Rate">
                    <input type="number" step="0.01" min="0" value={form.hourly_rate} onChange={e => setForm(f => ({ ...f, hourly_rate: e.target.value }))} />
                  </FormField>
                  <FormField label="Estimated Hours">
                    <input type="number" step="0.5" min="0" value={form.estimated_hours} onChange={e => setForm(f => ({ ...f, estimated_hours: e.target.value }))} />
                  </FormField>
                </>
              )}
              {form.fee_type === 'RETAINER' && (
                <FormField label="Monthly Retainer">
                  <input type="number" step="0.01" min="0" value={form.retainer_amount} onChange={e => setForm(f => ({ ...f, retainer_amount: e.target.value }))} />
                </FormField>
              )}
            </div>
            <FormField label="Terms & Conditions">
              <textarea value={form.terms_and_conditions} onChange={e => setForm(f => ({ ...f, terms_and_conditions: e.target.value }))} rows={4} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createEng.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
