import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatCurrency, formatDate } from '../utils/format';

const STATUS_COLORS = {
  DRAFT: '#6B7280', SENT: '#3B82F6', VIEWED: '#8B5CF6', PAID: '#10B981',
  PARTIAL: '#F59E0B', OVERDUE: '#EF4444', VOID: '#9CA3AF',
};

export default function ServiceBilling() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showPayment, setShowPayment] = useState(null);
  const [filters, setFilters] = useState({ status: '', client_id: '' });

  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  if (filters.client_id) params.set('client_id', filters.client_id);

  const { data } = useApiQuery(['service-invoices', filters], `/api/v1/service-invoices?${params}`);
  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');

  const createInvoice = useApiMutation('post', '/api/v1/service-invoices', { invalidate: [['service-invoices']] });
  const sendInvoice = useApiMutation('post', (body) => `/api/v1/service-invoices/${body.id}/send`, { invalidate: [['service-invoices']] });
  const voidInvoice = useApiMutation('post', (body) => `/api/v1/service-invoices/${body.id}/void`, { invalidate: [['service-invoices']] });
  const recordPayment = useApiMutation('post', (body) => `/api/v1/service-invoices/${body.invoice_id}/payments`, { invalidate: [['service-invoices']] });

  const [form, setForm] = useState({ client_id: '', invoice_date: '', due_date: '', notes: '', lines: [{ description: '', quantity: 1, unit_price: 0, service_type: '' }] });
  const [payForm, setPayForm] = useState({ payment_date: '', amount: '', payment_method: 'CHECK', reference_number: '' });

  function addLine() { setForm(f => ({ ...f, lines: [...f.lines, { description: '', quantity: 1, unit_price: 0, service_type: '' }] })); }
  function updateLine(i, field, val) { setForm(f => ({ ...f, lines: f.lines.map((l, j) => j === i ? { ...l, [field]: val } : l) })); }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await createInvoice.mutateAsync({
        ...form,
        lines: form.lines.map(l => ({ ...l, quantity: parseFloat(l.quantity), unit_price: parseFloat(l.unit_price) })),
        discount_amount: 0,
      });
      setShowAdd(false);
      setToast({ type: 'success', message: 'Invoice created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handlePayment(e) {
    e.preventDefault();
    try {
      await recordPayment.mutateAsync({ invoice_id: showPayment, ...payForm, amount: parseFloat(payForm.amount) });
      setShowPayment(null);
      setToast({ type: 'success', message: 'Payment recorded' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  const items = data?.items || [];
  const clientList = clients?.items || [];

  const columns = [
    { key: 'invoice_number', label: 'Invoice #' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'invoice_date', label: 'Date', render: (row) => formatDate(row.invoice_date) },
    { key: 'due_date', label: 'Due', render: (row) => formatDate(row.due_date) },
    { key: 'total_amount', label: 'Total', render: (row) => formatCurrency(row.total_amount) },
    { key: 'balance_due', label: 'Balance', render: (row) => formatCurrency(row.balance_due) },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
    { key: 'actions', label: 'Actions', render: (row) => (
      <div style={{ display: 'flex', gap: '4px' }}>
        {row.status === 'DRAFT' && <button className="btn btn--small btn--primary" onClick={() => sendInvoice.mutateAsync({ id: row.id })}>Send</button>}
        {['SENT', 'PARTIAL', 'OVERDUE'].includes(row.status) && <button className="btn btn--small btn--success" onClick={() => setShowPayment(row.id)}>Pay</button>}
        {row.status !== 'VOID' && row.status !== 'PAID' && <button className="btn btn--small btn--danger" onClick={() => voidInvoice.mutateAsync({ id: row.id })}>Void</button>}
      </div>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Service Billing</h1>
        <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ New Invoice</button>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
          <option value="">All</option>
          {Object.keys(STATUS_COLORS).map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <select value={filters.client_id} onChange={e => setFilters(f => ({ ...f, client_id: e.target.value }))}>
          <option value="">All Clients</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <DataTable columns={columns} rows={items} emptyMessage="No service invoices" />

      {showAdd && (
        <Modal title="New Service Invoice" onClose={() => setShowAdd(false)} wide>
          <form onSubmit={handleCreate}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <FormField label="Client" required>
                <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">Select...</option>
                  {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </FormField>
              <FormField label="Invoice Date" required>
                <input type="date" value={form.invoice_date} onChange={e => setForm(f => ({ ...f, invoice_date: e.target.value }))} required />
              </FormField>
              <FormField label="Due Date" required>
                <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} required />
              </FormField>
            </div>
            <h3 style={{ marginTop: '16px' }}>Line Items</h3>
            {form.lines.map((line, i) => (
              <div key={i} style={{ display: 'grid', gridTemplateColumns: '3fr 1fr 1fr 1fr', gap: '8px', marginBottom: '8px' }}>
                <input placeholder="Description" value={line.description} onChange={e => updateLine(i, 'description', e.target.value)} required />
                <input type="number" placeholder="Qty" min="0.01" step="0.01" value={line.quantity} onChange={e => updateLine(i, 'quantity', e.target.value)} />
                <input type="number" placeholder="Rate" min="0" step="0.01" value={line.unit_price} onChange={e => updateLine(i, 'unit_price', e.target.value)} />
                <span style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(line.quantity * line.unit_price)}</span>
              </div>
            ))}
            <button type="button" className="btn btn--small btn--outline" onClick={addLine}>+ Add Line</button>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createInvoice.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {showPayment && (
        <Modal title="Record Payment" onClose={() => setShowPayment(null)}>
          <form onSubmit={handlePayment}>
            <FormField label="Payment Date" required>
              <input type="date" value={payForm.payment_date} onChange={e => setPayForm(f => ({ ...f, payment_date: e.target.value }))} required />
            </FormField>
            <FormField label="Amount" required>
              <input type="number" step="0.01" min="0.01" value={payForm.amount} onChange={e => setPayForm(f => ({ ...f, amount: e.target.value }))} required />
            </FormField>
            <FormField label="Method">
              <select value={payForm.payment_method} onChange={e => setPayForm(f => ({ ...f, payment_method: e.target.value }))}>
                <option value="CHECK">Check</option>
                <option value="ACH">ACH</option>
                <option value="CREDIT_CARD">Credit Card</option>
                <option value="CASH">Cash</option>
              </select>
            </FormField>
            <FormField label="Reference #">
              <input value={payForm.reference_number} onChange={e => setPayForm(f => ({ ...f, reference_number: e.target.value }))} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowPayment(null)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={recordPayment.isPending}>Record Payment</button>
            </div>
          </form>
        </Modal>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
