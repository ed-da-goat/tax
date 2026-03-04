import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency, formatDate } from '../utils/format';

const PAGE_SIZE = 25;
const INVOICE_STATUSES = ['', 'DRAFT', 'PENDING_APPROVAL', 'SENT', 'OVERDUE', 'PAID', 'VOIDED'];

const emptyInvLine = () => ({ account_id: '', description: '', quantity: '1', unit_price: '' });

export default function AccountsReceivable() {
  const { clientId } = useParams();
  const api = useApi();
  const qc = useQueryClient();
  const { addToast } = useToast();

  const [page, setPage] = useState(0);
  const [statusFilter, setStatusFilter] = useState('');
  const [createModal, setCreateModal] = useState(false);
  const [invForm, setInvForm] = useState({ customer_name: '', invoice_number: '', invoice_date: '', due_date: '' });
  const [invLines, setInvLines] = useState([emptyInvLine()]);
  const [invErrors, setInvErrors] = useState({});
  const [detail, setDetail] = useState(null);

  // Payment modal
  const [payTarget, setPayTarget] = useState(null);
  const [payForm, setPayForm] = useState({ payment_date: '', amount: '', payment_method: '', reference_number: '' });

  // Account selection for approve/pay (AR and Cash accounts)
  const [actionModal, setActionModal] = useState(null); // { type: 'approve'|'pay', invoice: ... }
  const [arAccountId, setArAccountId] = useState('');
  const [cashAccountId, setCashAccountId] = useState('');

  // Queries
  const { data: client } = useApiQuery(['client', clientId], `/api/v1/clients/${clientId}`);

  const params = new URLSearchParams({ skip: String(page * PAGE_SIZE), limit: String(PAGE_SIZE) });
  if (statusFilter) params.set('status', statusFilter);
  const { data: invoicesData, isLoading } = useApiQuery(
    ['invoices', clientId, page, statusFilter],
    `/api/v1/clients/${clientId}/invoices?${params}`
  );
  const invoices = invoicesData?.items || [];

  const { data: accountsData } = useApiQuery(['accounts', clientId], `/api/v1/clients/${clientId}/accounts`);
  const accounts = (accountsData?.items || []).filter((a) => a.is_active);

  const accountGroups = {};
  accounts.forEach((a) => {
    if (!accountGroups[a.account_type]) accountGroups[a.account_type] = [];
    accountGroups[a.account_type].push(a);
  });

  const arAccounts = accounts.filter((a) => a.account_type === 'ASSET' && (a.account_name.toLowerCase().includes('receivable') || a.sub_type?.toLowerCase().includes('receivable')));
  const cashAccounts = accounts.filter((a) => a.account_type === 'ASSET' && (a.account_name.toLowerCase().includes('cash') || a.account_name.toLowerCase().includes('checking') || a.account_name.toLowerCase().includes('bank') || a.sub_type?.toLowerCase().includes('cash')));

  // Mutations
  const createInvMut = useMutation({
    mutationFn: (body) => api.post(`/api/v1/clients/${clientId}/invoices`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['invoices', clientId] }); addToast('success', 'Invoice created'); setCreateModal(false); },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  function invoiceAction(id, action, queryParams = '') {
    return api.post(`/api/v1/clients/${clientId}/invoices/${id}/${action}${queryParams}`);
  }

  const invActionMut = useMutation({
    mutationFn: ({ id, action, queryParams }) => invoiceAction(id, action, queryParams || ''),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices', clientId] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      addToast('success', 'Invoice updated');
      setDetail(null);
      setActionModal(null);
    },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  const payInvMut = useMutation({
    mutationFn: ({ id, body, queryParams }) => api.post(`/api/v1/clients/${clientId}/invoices/${id}/pay${queryParams}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['invoices', clientId] });
      addToast('success', 'Payment recorded');
      setPayTarget(null);
      setDetail(null);
      setActionModal(null);
    },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  function handleCreateSubmit(e) {
    e.preventDefault();
    const errs = {};
    if (!invForm.customer_name.trim()) errs.customer_name = 'Required';
    if (!invForm.invoice_date) errs.invoice_date = 'Required';
    if (!invForm.due_date) errs.due_date = 'Required';
    const validLines = invLines.filter((l) => l.account_id && l.unit_price);
    if (validLines.length === 0) errs.lines = 'At least one line required';
    if (Object.keys(errs).length) { setInvErrors(errs); return; }
    createInvMut.mutate({
      ...invForm,
      lines: validLines.map((l) => ({
        account_id: l.account_id,
        description: l.description || null,
        quantity: String(l.quantity || '1'),
        unit_price: String(l.unit_price),
      })),
    });
  }

  function handleApproveWithAccount() {
    if (!arAccountId) return;
    invActionMut.mutate({
      id: actionModal.invoice.id,
      action: 'approve',
      queryParams: `?ar_account_id=${arAccountId}`,
    });
  }

  function handlePayWithAccounts(e) {
    e.preventDefault();
    if (!arAccountId || !cashAccountId || !payForm.payment_date || !payForm.amount) return;
    payInvMut.mutate({
      id: actionModal.invoice.id,
      body: { ...payForm, amount: String(payForm.amount) },
      queryParams: `?cash_account_id=${cashAccountId}&ar_account_id=${arAccountId}`,
    });
  }

  const columns = [
    { key: 'invoice_number', label: 'Invoice #' },
    { key: 'customer_name', label: 'Customer' },
    { key: 'invoice_date', label: 'Date', render: (v) => formatDate(v) },
    { key: 'due_date', label: 'Due Date', render: (v) => formatDate(v) },
    { key: 'total_amount', label: 'Amount', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
    {
      key: 'actions', label: '', render: (_, row) => (
        <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); setDetail(row); }}>View</button>
      ),
    },
  ];

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/clients">Clients</Link>
        <span className="breadcrumb-sep">/</span>
        <Link to={`/clients/${clientId}`}>{client?.name || 'Client'}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>Accounts Receivable</span>
      </div>

      <div className="page-header">
        <h1 className="page-title">Accounts Receivable</h1>
        <button className="btn btn--primary" onClick={() => {
          setInvForm({ customer_name: '', invoice_number: '', invoice_date: new Date().toISOString().split('T')[0], due_date: '' });
          setInvLines([emptyInvLine()]);
          setInvErrors({});
          setCreateModal(true);
        }}>Create Invoice</button>
      </div>

      <div className="filter-bar">
        <div className="form-field">
          <select className="form-input form-select" value={statusFilter}
            onChange={(e) => { setStatusFilter(e.target.value); setPage(0); }}>
            <option value="">All Statuses</option>
            {INVOICE_STATUSES.filter(Boolean).map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
          </select>
        </div>
      </div>

      <DataTable columns={columns} data={invoices} total={invoicesData?.total || 0} page={page} pageSize={PAGE_SIZE}
        onPageChange={setPage} loading={isLoading} emptyMessage="No invoices." />

      {/* Create Invoice Modal */}
      <Modal isOpen={createModal} onClose={() => setCreateModal(false)} title="Create Invoice" size="lg">
        <form onSubmit={handleCreateSubmit}>
          {invErrors.lines && <div className="alert alert--error">{invErrors.lines}</div>}
          <div className="form-row">
            <FormField label="Customer Name" error={invErrors.customer_name}>
              <input className="form-input" value={invForm.customer_name} onChange={(e) => setInvForm({ ...invForm, customer_name: e.target.value })} autoFocus />
            </FormField>
            <FormField label="Invoice #">
              <input className="form-input" value={invForm.invoice_number} onChange={(e) => setInvForm({ ...invForm, invoice_number: e.target.value })} />
            </FormField>
          </div>
          <div className="form-row">
            <FormField label="Invoice Date" error={invErrors.invoice_date}>
              <input className="form-input" type="date" value={invForm.invoice_date} onChange={(e) => setInvForm({ ...invForm, invoice_date: e.target.value })} />
            </FormField>
            <FormField label="Due Date" error={invErrors.due_date}>
              <input className="form-input" type="date" value={invForm.due_date} onChange={(e) => setInvForm({ ...invForm, due_date: e.target.value })} />
            </FormField>
          </div>

          <div className="section-header mt-16">
            <h3 className="section-title">Line Items</h3>
            <button type="button" className="btn btn--outline btn--small" onClick={() => setInvLines([...invLines, emptyInvLine()])}>Add Line</button>
          </div>
          <table className="je-lines-table">
            <thead><tr><th>Account</th><th>Description</th><th style={{ textAlign: 'right' }}>Qty</th><th style={{ textAlign: 'right' }}>Unit Price</th><th style={{ textAlign: 'right' }}>Amount</th><th></th></tr></thead>
            <tbody>
              {invLines.map((line, i) => {
                const amt = (parseFloat(line.quantity) || 0) * (parseFloat(line.unit_price) || 0);
                return (
                  <tr key={i}>
                    <td>
                      <select className="form-input form-select" value={line.account_id}
                        onChange={(e) => { const u = [...invLines]; u[i] = { ...u[i], account_id: e.target.value }; setInvLines(u); }}>
                        <option value="">Select...</option>
                        {Object.entries(accountGroups).map(([type, accts]) => (
                          <optgroup key={type} label={type}>
                            {accts.map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
                          </optgroup>
                        ))}
                      </select>
                    </td>
                    <td><input className="form-input" value={line.description} onChange={(e) => { const u = [...invLines]; u[i] = { ...u[i], description: e.target.value }; setInvLines(u); }} /></td>
                    <td><input className="form-input text-right" type="number" min="1" step="1" value={line.quantity}
                      onChange={(e) => { const u = [...invLines]; u[i] = { ...u[i], quantity: e.target.value }; setInvLines(u); }} style={{ width: 70 }} /></td>
                    <td><input className="form-input text-right" type="number" min="0" step="0.01" value={line.unit_price}
                      onChange={(e) => { const u = [...invLines]; u[i] = { ...u[i], unit_price: e.target.value }; setInvLines(u); }} /></td>
                    <td className="text-right">{formatCurrency(amt)}</td>
                    <td>{invLines.length > 1 && <button type="button" className="btn btn--small btn--danger" onClick={() => setInvLines(invLines.filter((_, j) => j !== i))}>X</button>}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <div className="je-totals">
            <span>Total: {formatCurrency(invLines.reduce((s, l) => s + (parseFloat(l.quantity) || 0) * (parseFloat(l.unit_price) || 0), 0))}</span>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={() => setCreateModal(false)}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={createInvMut.isPending}>Create Invoice</button>
          </div>
        </form>
      </Modal>

      {/* Invoice Detail Modal */}
      <Modal isOpen={!!detail} onClose={() => setDetail(null)} title={`Invoice ${detail?.invoice_number || ''}`} size="lg">
        {detail && (
          <>
            <div className="form-row mb-16">
              <div><strong>Customer:</strong> {detail.customer_name}</div>
              <div><strong>Status:</strong> <StatusBadge status={detail.status} /></div>
              <div><strong>Total:</strong> {formatCurrency(detail.total_amount)}</div>
            </div>
            <div className="form-row mb-16">
              <div><strong>Invoice Date:</strong> {formatDate(detail.invoice_date)}</div>
              <div><strong>Due Date:</strong> {formatDate(detail.due_date)}</div>
            </div>

            {detail.lines?.length > 0 && (
              <table className="table mb-16">
                <thead><tr><th>Description</th><th style={{ textAlign: 'right' }}>Qty</th><th style={{ textAlign: 'right' }}>Price</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                <tbody>
                  {detail.lines.map((l) => (
                    <tr key={l.id}><td>{l.description || '--'}</td><td className="text-right">{l.quantity}</td><td className="text-right">{formatCurrency(l.unit_price)}</td><td className="text-right">{formatCurrency(l.amount)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}

            {detail.payments?.length > 0 && (
              <>
                <h4 className="mb-8">Payments</h4>
                <table className="table mb-16">
                  <thead><tr><th>Date</th><th>Method</th><th>Reference</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                  <tbody>
                    {detail.payments.map((p) => (
                      <tr key={p.id}><td>{formatDate(p.payment_date)}</td><td>{p.payment_method || '--'}</td><td>{p.reference_number || '--'}</td><td className="text-right">{formatCurrency(p.amount)}</td></tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            <div className="form-actions">
              {detail.status === 'DRAFT' && (
                <button className="btn btn--primary" onClick={() => invActionMut.mutate({ id: detail.id, action: 'submit' })}>Submit for Approval</button>
              )}
              <RoleGate role="CPA_OWNER">
                {detail.status === 'PENDING_APPROVAL' && (
                  <button className="btn btn--primary" onClick={() => {
                    setArAccountId(arAccounts[0]?.id || '');
                    setActionModal({ type: 'approve', invoice: detail });
                  }}>Approve</button>
                )}
                {['SENT', 'OVERDUE', 'PAID'].includes(detail.status) && (
                  <button className="btn btn--danger" onClick={() => {
                    setArAccountId(arAccounts[0]?.id || '');
                    invActionMut.mutate({ id: detail.id, action: 'void', queryParams: arAccounts[0] ? `?ar_account_id=${arAccounts[0].id}` : '' });
                  }}>Void</button>
                )}
              </RoleGate>
              {(detail.status === 'SENT' || detail.status === 'OVERDUE') && (
                <button className="btn btn--primary" onClick={() => {
                  setArAccountId(arAccounts[0]?.id || '');
                  setCashAccountId(cashAccounts[0]?.id || '');
                  setPayForm({ payment_date: new Date().toISOString().split('T')[0], amount: '', payment_method: '', reference_number: '' });
                  setActionModal({ type: 'pay', invoice: detail });
                }}>Record Payment</button>
              )}
            </div>
          </>
        )}
      </Modal>

      {/* Approve with AR account selection */}
      <Modal isOpen={actionModal?.type === 'approve'} onClose={() => setActionModal(null)} title="Select AR Account" size="sm">
        <FormField label="Accounts Receivable Account">
          <select className="form-input form-select" value={arAccountId} onChange={(e) => setArAccountId(e.target.value)}>
            <option value="">Select AR account...</option>
            {arAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
            {arAccounts.length === 0 && accounts.filter((a) => a.account_type === 'ASSET').map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
          </select>
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setActionModal(null)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleApproveWithAccount} disabled={!arAccountId || invActionMut.isPending}>Approve</button>
        </div>
      </Modal>

      {/* Pay with account selection */}
      <Modal isOpen={actionModal?.type === 'pay'} onClose={() => setActionModal(null)} title="Record Payment" size="md">
        <form onSubmit={handlePayWithAccounts}>
          <div className="form-row">
            <FormField label="AR Account">
              <select className="form-input form-select" value={arAccountId} onChange={(e) => setArAccountId(e.target.value)}>
                <option value="">Select...</option>
                {arAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
                {arAccounts.length === 0 && accounts.filter((a) => a.account_type === 'ASSET').map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
              </select>
            </FormField>
            <FormField label="Cash/Bank Account">
              <select className="form-input form-select" value={cashAccountId} onChange={(e) => setCashAccountId(e.target.value)}>
                <option value="">Select...</option>
                {cashAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
                {cashAccounts.length === 0 && accounts.filter((a) => a.account_type === 'ASSET').map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
              </select>
            </FormField>
          </div>
          <FormField label="Payment Date">
            <input className="form-input" type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} />
          </FormField>
          <FormField label="Amount">
            <input className="form-input" type="number" min="0" step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} />
          </FormField>
          <div className="form-row">
            <FormField label="Method">
              <select className="form-input form-select" value={payForm.payment_method} onChange={(e) => setPayForm({ ...payForm, payment_method: e.target.value })}>
                <option value="">Select...</option>
                <option value="Check">Check</option>
                <option value="ACH">ACH</option>
                <option value="Wire">Wire</option>
                <option value="Cash">Cash</option>
                <option value="Credit Card">Credit Card</option>
              </select>
            </FormField>
            <FormField label="Reference #">
              <input className="form-input" value={payForm.reference_number} onChange={(e) => setPayForm({ ...payForm, reference_number: e.target.value })} />
            </FormField>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={() => setActionModal(null)}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={!arAccountId || !cashAccountId || payInvMut.isPending}>Record Payment</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
