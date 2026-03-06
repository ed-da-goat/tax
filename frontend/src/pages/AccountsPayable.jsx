import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import Tabs from '../components/Tabs';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency, formatDate } from '../utils/format';

const PAGE_SIZE = 25;
const BILL_STATUSES = ['', 'DRAFT', 'PENDING_APPROVAL', 'APPROVED', 'PAID', 'VOIDED'];

const emptyVendor = { name: '', address: '', city: '', state: 'GA', zip: '', phone: '', email: '' };
const emptyBillLine = () => ({ account_id: '', description: '', amount: '' });

export default function AccountsPayable() {
  const { clientId } = useParams();
  const api = useApi();
  const qc = useQueryClient();
  const { addToast } = useToast();

  const [tab, setTab] = useState('bills');

  // Vendor state
  const [vendorPage, setVendorPage] = useState(0);
  const [vendorModal, setVendorModal] = useState(false);
  const [editingVendor, setEditingVendor] = useState(null);
  const [vendorForm, setVendorForm] = useState(emptyVendor);
  const [vendorErrors, setVendorErrors] = useState({});
  const [archiveTarget, setArchiveTarget] = useState(null);

  // Bill state
  const [billPage, setBillPage] = useState(0);
  const [billStatusFilter, setBillStatusFilter] = useState('');
  const [billModal, setBillModal] = useState(false);
  const [billForm, setBillForm] = useState({ vendor_id: '', bill_number: '', bill_date: '', due_date: '' });
  const [billLines, setBillLines] = useState([emptyBillLine()]);
  const [billErrors, setBillErrors] = useState({});
  const [billDetail, setBillDetail] = useState(null);

  // Payment modal
  const [payTarget, setPayTarget] = useState(null);
  const [payForm, setPayForm] = useState({ payment_date: '', amount: '', payment_method: '', reference_number: '' });
  const [printingCheckId, setPrintingCheckId] = useState(null);

  // Queries
  const { data: client } = useApiQuery(['client', clientId], `/api/v1/clients/${clientId}`);

  const vendorParams = new URLSearchParams({ skip: String(vendorPage * PAGE_SIZE), limit: String(PAGE_SIZE) });
  const { data: vendorsData, isLoading: vendorsLoading } = useApiQuery(
    ['vendors', clientId, vendorPage],
    `/api/v1/clients/${clientId}/vendors?${vendorParams}`
  );
  const vendors = vendorsData?.items || [];

  const billParams = new URLSearchParams({ skip: String(billPage * PAGE_SIZE), limit: String(PAGE_SIZE) });
  if (billStatusFilter) billParams.set('status', billStatusFilter);
  const { data: billsData, isLoading: billsLoading } = useApiQuery(
    ['bills', clientId, billPage, billStatusFilter],
    `/api/v1/clients/${clientId}/bills?${billParams}`
  );
  const bills = billsData?.items || [];

  const { data: accountsData } = useApiQuery(['accounts', clientId], `/api/v1/clients/${clientId}/accounts`);
  const accounts = (accountsData?.items || []).filter((a) => a.is_active);

  const accountGroups = {};
  accounts.forEach((a) => {
    if (!accountGroups[a.account_type]) accountGroups[a.account_type] = [];
    accountGroups[a.account_type].push(a);
  });

  // Vendor mutations
  const createVendorMut = useMutation({
    mutationFn: (body) => api.post(`/api/v1/clients/${clientId}/vendors`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vendors', clientId] }); addToast('success', 'Vendor created'); setVendorModal(false); },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });
  const updateVendorMut = useMutation({
    mutationFn: ({ id, body }) => api.put(`/api/v1/clients/${clientId}/vendors/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vendors', clientId] }); addToast('success', 'Vendor updated'); setVendorModal(false); },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });
  const archiveVendorMut = useMutation({
    mutationFn: (id) => api.delete(`/api/v1/clients/${clientId}/vendors/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['vendors', clientId] }); addToast('success', 'Vendor archived'); setArchiveTarget(null); },
  });

  // Bill mutations
  const createBillMut = useMutation({
    mutationFn: (body) => api.post(`/api/v1/clients/${clientId}/bills`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['bills', clientId] }); addToast('success', 'Bill created'); setBillModal(false); },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  function billAction(id, action) {
    return api.post(`/api/v1/clients/${clientId}/bills/${id}/${action}`);
  }

  const billActionMut = useMutation({
    mutationFn: ({ id, action }) => billAction(id, action),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bills', clientId] });
      qc.invalidateQueries({ queryKey: ['dashboard'] });
      addToast('success', 'Bill updated');
      setBillDetail(null);
    },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  const payBillMut = useMutation({
    mutationFn: ({ id, body }) => api.post(`/api/v1/clients/${clientId}/bills/${id}/pay`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['bills', clientId] });
      addToast('success', 'Payment recorded');
      setPayTarget(null);
      setBillDetail(null);
    },
    onError: (e) => addToast('error', e.response?.data?.detail || 'Failed'),
  });

  // Vendor handlers
  function openVendorCreate() {
    setEditingVendor(null); setVendorForm(emptyVendor); setVendorErrors({}); setVendorModal(true);
  }
  function openVendorEdit(v) {
    setEditingVendor(v);
    setVendorForm({ name: v.name, address: v.address || '', city: v.city || '', state: v.state || 'GA', zip: v.zip || '', phone: v.phone || '', email: v.email || '' });
    setVendorErrors({});
    setVendorModal(true);
  }
  function handleVendorSubmit(e) {
    e.preventDefault();
    if (!vendorForm.name.trim()) { setVendorErrors({ name: 'Required' }); return; }
    if (editingVendor) updateVendorMut.mutate({ id: editingVendor.id, body: vendorForm });
    else createVendorMut.mutate(vendorForm);
  }

  // Bill handlers
  function openBillCreate() {
    setBillForm({ vendor_id: '', bill_number: '', bill_date: new Date().toISOString().split('T')[0], due_date: '' });
    setBillLines([emptyBillLine()]);
    setBillErrors({});
    setBillModal(true);
  }
  function handleBillSubmit(e) {
    e.preventDefault();
    const errs = {};
    if (!billForm.vendor_id) errs.vendor_id = 'Required';
    if (!billForm.bill_date) errs.bill_date = 'Required';
    if (!billForm.due_date) errs.due_date = 'Required';
    const validLines = billLines.filter((l) => l.account_id && l.amount);
    if (validLines.length === 0) errs.lines = 'At least one line required';
    if (Object.keys(errs).length) { setBillErrors(errs); return; }
    createBillMut.mutate({
      ...billForm,
      lines: validLines.map((l) => ({ account_id: l.account_id, description: l.description || null, amount: String(l.amount) })),
    });
  }

  function handlePaySubmit(e) {
    e.preventDefault();
    if (!payForm.payment_date || !payForm.amount) return;
    payBillMut.mutate({
      id: payTarget.id,
      body: { ...payForm, amount: String(payForm.amount) },
    });
  }

  // Print check handler
  async function handlePrintCheck(billId, paymentId) {
    setPrintingCheckId(paymentId);
    try {
      const res = await api.post(
        `/api/v1/clients/${clientId}/bills/${billId}/payments/${paymentId}/print-check`,
        {},
        { responseType: 'blob' }
      );
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `check-bill-${billId}-payment-${paymentId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
      addToast('success', 'Check PDF downloaded');
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to print check');
    } finally {
      setPrintingCheckId(null);
    }
  }

  // Vendor columns
  const vendorCols = [
    { key: 'name', label: 'Name' },
    { key: 'city', label: 'City' },
    { key: 'state', label: 'State' },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    {
      key: 'actions', label: '', render: (_, row) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); openVendorEdit(row); }}>Edit</button>
          <RoleGate role="CPA_OWNER">
            <button className="btn btn--small btn--danger" onClick={(e) => { e.stopPropagation(); setArchiveTarget(row); }}>Archive</button>
          </RoleGate>
        </div>
      ),
    },
  ];

  // Bill columns
  const billCols = [
    { key: 'bill_number', label: 'Bill #' },
    { key: 'vendor_id', label: 'Vendor', render: (v) => vendors.find((vn) => vn.id === v)?.name || '--' },
    { key: 'bill_date', label: 'Bill Date', render: (v) => formatDate(v) },
    { key: 'due_date', label: 'Due Date', render: (v) => formatDate(v) },
    { key: 'total_amount', label: 'Amount', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
    {
      key: 'actions', label: '', render: (_, row) => (
        <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); setBillDetail(row); }}>View</button>
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
        <span>Accounts Payable</span>
      </div>

      <h1 className="page-title">Accounts Payable</h1>

      <Tabs tabs={[{ key: 'bills', label: 'Bills' }, { key: 'vendors', label: 'Vendors' }]} activeTab={tab} onTabChange={setTab} />

      {/* Bills Tab */}
      {tab === 'bills' && (
        <>
          <div className="section-header">
            <div className="filter-bar" style={{ marginBottom: 0 }}>
              <div className="form-field">
                <select className="form-input form-select" value={billStatusFilter}
                  onChange={(e) => { setBillStatusFilter(e.target.value); setBillPage(0); }}>
                  <option value="">All Statuses</option>
                  {BILL_STATUSES.filter(Boolean).map((s) => <option key={s} value={s}>{s.replace(/_/g, ' ')}</option>)}
                </select>
              </div>
            </div>
            <button className="btn btn--primary btn--small" onClick={openBillCreate}>Create Bill</button>
          </div>
          <DataTable columns={billCols} data={bills} total={billsData?.total || 0} page={billPage} pageSize={PAGE_SIZE}
            onPageChange={setBillPage} loading={billsLoading} emptyMessage="No bills." />
        </>
      )}

      {/* Vendors Tab */}
      {tab === 'vendors' && (
        <>
          <div className="section-header">
            <h2 className="section-title">Vendors</h2>
            <button className="btn btn--primary btn--small" onClick={openVendorCreate}>Add Vendor</button>
          </div>
          <DataTable columns={vendorCols} data={vendors} total={vendorsData?.total || 0} page={vendorPage} pageSize={PAGE_SIZE}
            onPageChange={setVendorPage} loading={vendorsLoading} emptyMessage="No vendors." />
        </>
      )}

      {/* Vendor Create/Edit Modal */}
      <Modal isOpen={vendorModal} onClose={() => setVendorModal(false)} title={editingVendor ? 'Edit Vendor' : 'Add Vendor'} size="md">
        <form onSubmit={handleVendorSubmit}>
          <FormField label="Name" error={vendorErrors.name}>
            <input className="form-input" value={vendorForm.name} onChange={(e) => setVendorForm({ ...vendorForm, name: e.target.value })} autoFocus />
          </FormField>
          <FormField label="Address">
            <input className="form-input" value={vendorForm.address} onChange={(e) => setVendorForm({ ...vendorForm, address: e.target.value })} />
          </FormField>
          <div className="form-row">
            <FormField label="City"><input className="form-input" value={vendorForm.city} onChange={(e) => setVendorForm({ ...vendorForm, city: e.target.value })} /></FormField>
            <FormField label="State"><input className="form-input" value={vendorForm.state} onChange={(e) => setVendorForm({ ...vendorForm, state: e.target.value })} maxLength={2} /></FormField>
            <FormField label="ZIP"><input className="form-input" value={vendorForm.zip} onChange={(e) => setVendorForm({ ...vendorForm, zip: e.target.value })} /></FormField>
          </div>
          <div className="form-row">
            <FormField label="Phone"><input className="form-input" value={vendorForm.phone} onChange={(e) => setVendorForm({ ...vendorForm, phone: e.target.value })} /></FormField>
            <FormField label="Email"><input className="form-input" type="email" value={vendorForm.email} onChange={(e) => setVendorForm({ ...vendorForm, email: e.target.value })} /></FormField>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={() => setVendorModal(false)}>Cancel</button>
            <button type="submit" className="btn btn--primary">{editingVendor ? 'Save' : 'Create'}</button>
          </div>
        </form>
      </Modal>

      {/* Archive Vendor Confirm */}
      <ConfirmDialog isOpen={!!archiveTarget} onCancel={() => setArchiveTarget(null)}
        onConfirm={() => archiveVendorMut.mutate(archiveTarget.id)}
        title="Archive Vendor" message={`Archive "${archiveTarget?.name}"?`} confirmLabel="Archive" />

      {/* Create Bill Modal */}
      <Modal isOpen={billModal} onClose={() => setBillModal(false)} title="Create Bill" size="lg">
        <form onSubmit={handleBillSubmit}>
          {billErrors.lines && <div className="alert alert--error">{billErrors.lines}</div>}
          <div className="form-row">
            <FormField label="Vendor" error={billErrors.vendor_id}>
              <select className="form-input form-select" value={billForm.vendor_id}
                onChange={(e) => setBillForm({ ...billForm, vendor_id: e.target.value })}>
                <option value="">Select vendor...</option>
                {vendors.map((v) => <option key={v.id} value={v.id}>{v.name}</option>)}
              </select>
            </FormField>
            <FormField label="Bill #">
              <input className="form-input" value={billForm.bill_number} onChange={(e) => setBillForm({ ...billForm, bill_number: e.target.value })} />
            </FormField>
          </div>
          <div className="form-row">
            <FormField label="Bill Date" error={billErrors.bill_date}>
              <input className="form-input" type="date" value={billForm.bill_date} onChange={(e) => setBillForm({ ...billForm, bill_date: e.target.value })} />
            </FormField>
            <FormField label="Due Date" error={billErrors.due_date}>
              <input className="form-input" type="date" value={billForm.due_date} onChange={(e) => setBillForm({ ...billForm, due_date: e.target.value })} />
            </FormField>
          </div>

          <div className="section-header mt-16">
            <h3 className="section-title">Line Items</h3>
            <button type="button" className="btn btn--outline btn--small" onClick={() => setBillLines([...billLines, emptyBillLine()])}>Add Line</button>
          </div>
          <table className="je-lines-table">
            <thead><tr><th>Account</th><th>Description</th><th style={{ textAlign: 'right' }}>Amount</th><th></th></tr></thead>
            <tbody>
              {billLines.map((line, i) => (
                <tr key={i}>
                  <td>
                    <select className="form-input form-select" value={line.account_id}
                      onChange={(e) => { const u = [...billLines]; u[i] = { ...u[i], account_id: e.target.value }; setBillLines(u); }}>
                      <option value="">Select...</option>
                      {Object.entries(accountGroups).map(([type, accts]) => (
                        <optgroup key={type} label={type}>
                          {accts.map((a) => <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>)}
                        </optgroup>
                      ))}
                    </select>
                  </td>
                  <td><input className="form-input" value={line.description} onChange={(e) => { const u = [...billLines]; u[i] = { ...u[i], description: e.target.value }; setBillLines(u); }} /></td>
                  <td><input className="form-input text-right" type="number" min="0" step="0.01" value={line.amount}
                    onChange={(e) => { const u = [...billLines]; u[i] = { ...u[i], amount: e.target.value }; setBillLines(u); }} /></td>
                  <td>
                    {billLines.length > 1 && <button type="button" className="btn btn--small btn--danger" onClick={() => setBillLines(billLines.filter((_, j) => j !== i))}>X</button>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="je-totals">
            <span>Total: {formatCurrency(billLines.reduce((s, l) => s + (parseFloat(l.amount) || 0), 0))}</span>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={() => setBillModal(false)}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={createBillMut.isPending}>Create Bill</button>
          </div>
        </form>
      </Modal>

      {/* Bill Detail Modal */}
      <Modal isOpen={!!billDetail} onClose={() => setBillDetail(null)} title={`Bill ${billDetail?.bill_number || ''}`} size="lg">
        {billDetail && (
          <>
            <div className="form-row mb-16">
              <div><strong>Vendor:</strong> {vendors.find((v) => v.id === billDetail.vendor_id)?.name || '--'}</div>
              <div><strong>Status:</strong> <StatusBadge status={billDetail.status} /></div>
              <div><strong>Total:</strong> {formatCurrency(billDetail.total_amount)}</div>
            </div>
            <div className="form-row mb-16">
              <div><strong>Bill Date:</strong> {formatDate(billDetail.bill_date)}</div>
              <div><strong>Due Date:</strong> {formatDate(billDetail.due_date)}</div>
            </div>

            {billDetail.lines?.length > 0 && (
              <table className="table mb-16">
                <thead><tr><th>Description</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                <tbody>
                  {billDetail.lines.map((l) => (
                    <tr key={l.id}><td>{l.description || '--'}</td><td className="text-right">{formatCurrency(l.amount)}</td></tr>
                  ))}
                </tbody>
              </table>
            )}

            {billDetail.payments?.length > 0 && (
              <>
                <h4 className="mb-8">Payments</h4>
                <table className="table mb-16">
                  <thead><tr><th>Date</th><th>Method</th><th>Reference</th><th style={{ textAlign: 'right' }}>Amount</th><th></th></tr></thead>
                  <tbody>
                    {billDetail.payments.map((p) => (
                      <tr key={p.id}>
                        <td>{formatDate(p.payment_date)}</td>
                        <td>{p.payment_method || '--'}</td>
                        <td>{p.reference_number || '--'}</td>
                        <td className="text-right">{formatCurrency(p.amount)}</td>
                        <td>
                          {p.payment_method === 'Check' && (
                            <RoleGate role="CPA_OWNER">
                              <button
                                className="btn btn--small btn--outline"
                                disabled={printingCheckId === p.id}
                                onClick={() => handlePrintCheck(billDetail.id, p.id)}
                              >
                                {printingCheckId === p.id ? 'Printing...' : 'Print Check'}
                              </button>
                            </RoleGate>
                          )}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </>
            )}

            <div className="form-actions">
              {billDetail.status === 'DRAFT' && (
                <button className="btn btn--primary" onClick={() => billActionMut.mutate({ id: billDetail.id, action: 'submit' })}>Submit for Approval</button>
              )}
              <RoleGate role="CPA_OWNER">
                {billDetail.status === 'PENDING_APPROVAL' && (
                  <button className="btn btn--primary" onClick={() => billActionMut.mutate({ id: billDetail.id, action: 'approve' })}>Approve</button>
                )}
                {(billDetail.status === 'APPROVED' || billDetail.status === 'PAID') && (
                  <button className="btn btn--danger" onClick={() => billActionMut.mutate({ id: billDetail.id, action: 'void' })}>Void</button>
                )}
              </RoleGate>
              {billDetail.status === 'APPROVED' && (
                <button className="btn btn--primary" onClick={() => {
                  setPayTarget(billDetail);
                  setPayForm({ payment_date: new Date().toISOString().split('T')[0], amount: '', payment_method: '', reference_number: '' });
                }}>Record Payment</button>
              )}
            </div>
          </>
        )}
      </Modal>

      {/* Payment Modal */}
      <Modal isOpen={!!payTarget} onClose={() => setPayTarget(null)} title="Record Payment" size="sm">
        <form onSubmit={handlePaySubmit}>
          <FormField label="Payment Date">
            <input className="form-input" type="date" value={payForm.payment_date} onChange={(e) => setPayForm({ ...payForm, payment_date: e.target.value })} />
          </FormField>
          <FormField label="Amount">
            <input className="form-input" type="number" min="0" step="0.01" value={payForm.amount} onChange={(e) => setPayForm({ ...payForm, amount: e.target.value })} />
          </FormField>
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
          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={() => setPayTarget(null)}>Cancel</button>
            <button type="submit" className="btn btn--primary" disabled={payBillMut.isPending}>Record Payment</button>
          </div>
        </form>
      </Modal>
    </div>
  );
}
