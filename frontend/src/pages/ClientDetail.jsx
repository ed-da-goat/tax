import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import useAuth from '../hooks/useAuth';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import Tabs from '../components/Tabs';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import { FormField, SelectField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency, formatDate, formatEntityType } from '../utils/format';

const ACCOUNT_TYPES = [
  { value: '', label: 'All Types' },
  { value: 'ASSET', label: 'Asset' },
  { value: 'LIABILITY', label: 'Liability' },
  { value: 'EQUITY', label: 'Equity' },
  { value: 'REVENUE', label: 'Revenue' },
  { value: 'EXPENSE', label: 'Expense' },
];

const JE_STATUSES = [
  { value: '', label: 'All' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'PENDING_APPROVAL', label: 'Pending' },
  { value: 'POSTED', label: 'Posted' },
  { value: 'VOID', label: 'Void' },
];

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'accounts', label: 'Chart of Accounts' },
  { key: 'journal', label: 'Journal Entries' },
];

export default function ClientDetail() {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const api = useApi();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { hasRole } = useAuth();

  const [tab, setTab] = useState('overview');
  const [accountTypeFilter, setAccountTypeFilter] = useState('');
  const [jeStatus, setJeStatus] = useState('');
  const [jePage, setJePage] = useState(0);

  // Add account modal
  const [showAddAccount, setShowAddAccount] = useState(false);
  const [accountForm, setAccountForm] = useState({
    account_number: '', account_name: '', account_type: '', sub_type: '',
  });
  const [accountErrors, setAccountErrors] = useState({});

  // Data queries
  const { data: client, isLoading: clientLoading } = useApiQuery(
    ['client', clientId],
    `/api/v1/clients/${clientId}`
  );

  const { data: accountsData } = useApiQuery(
    ['accounts', clientId, accountTypeFilter],
    `/api/v1/clients/${clientId}/accounts${accountTypeFilter ? `?account_type=${accountTypeFilter}` : ''}`
  );

  const jeParams = new URLSearchParams({ skip: String(jePage * 25), limit: '25' });
  if (jeStatus) jeParams.set('status', jeStatus);

  const { data: jeData } = useApiQuery(
    ['journal-entries', clientId, jeStatus, jePage],
    `/api/v1/clients/${clientId}/journal-entries?${jeParams}`
  );

  const { data: trialBalance } = useApiQuery(
    ['trial-balance', clientId],
    `/api/v1/clients/${clientId}/trial-balance`
  );

  const cloneMutation = useMutation({
    mutationFn: () => api.post(`/api/v1/clients/${clientId}/accounts/clone-template`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts', clientId] });
      addToast('success', 'Template accounts cloned');
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to clone accounts'),
  });

  const createAccountMutation = useMutation({
    mutationFn: (body) => api.post(`/api/v1/clients/${clientId}/accounts`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['accounts', clientId] });
      addToast('success', 'Account created');
      setShowAddAccount(false);
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to create account'),
  });

  function handleAddAccount(e) {
    e.preventDefault();
    const errs = {};
    if (!accountForm.account_number.trim()) errs.account_number = 'Required';
    if (!accountForm.account_name.trim()) errs.account_name = 'Required';
    if (!accountForm.account_type) errs.account_type = 'Required';
    if (Object.keys(errs).length > 0) { setAccountErrors(errs); return; }
    createAccountMutation.mutate(accountForm);
  }

  if (clientLoading) return <div className="page"><p>Loading...</p></div>;
  if (!client) return <div className="page"><p>Client not found.</p></div>;

  const accounts = accountsData?.items || [];
  const journalEntries = jeData?.items || [];
  const tbRows = trialBalance?.rows || [];

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/clients">Clients</Link>
        <span className="breadcrumb-sep">/</span>
        <span>{client.name}</span>
      </div>

      <div className="page-header">
        <div>
          <h1 className="page-title">{client.name}</h1>
          <span className="text-muted">{formatEntityType(client.entity_type)}</span>
          {client.ein && <span className="text-muted" style={{ marginLeft: 12 }}>EIN: {client.ein}</span>}
        </div>
      </div>

      <div className="quick-actions">
        <button className="btn btn--primary" onClick={() => navigate(`/clients/${clientId}/journal-entries/new`)}>
          New Journal Entry
        </button>
        <button className="btn btn--outline" onClick={() => navigate(`/clients/${clientId}/ap`)}>
          Accounts Payable
        </button>
        <button className="btn btn--outline" onClick={() => navigate(`/clients/${clientId}/ar`)}>
          Accounts Receivable
        </button>
        <RoleGate role="CPA_OWNER">
          {accounts.length === 0 && (
            <button
              className="btn btn--outline"
              onClick={() => cloneMutation.mutate()}
              disabled={cloneMutation.isPending}
            >
              Clone Template Accounts
            </button>
          )}
        </RoleGate>
      </div>

      <Tabs tabs={TABS} activeTab={tab} onTabChange={setTab} />

      {/* Overview Tab */}
      {tab === 'overview' && (
        <>
          <div className="section-header">
            <h2 className="section-title">Trial Balance</h2>
          </div>
          {tbRows.length === 0 ? (
            <p className="empty-state">No posted entries yet.</p>
          ) : (
            <table className="table">
              <thead>
                <tr>
                  <th>Account #</th>
                  <th>Account Name</th>
                  <th style={{ textAlign: 'right' }}>Debits</th>
                  <th style={{ textAlign: 'right' }}>Credits</th>
                  <th style={{ textAlign: 'right' }}>Balance</th>
                </tr>
              </thead>
              <tbody>
                {tbRows.map((r, i) => (
                  <tr key={i}>
                    <td className="font-mono">{r.account_number}</td>
                    <td>{r.account_name}</td>
                    <td className="text-right">{formatCurrency(r.total_debits)}</td>
                    <td className="text-right">{formatCurrency(r.total_credits)}</td>
                    <td className="text-right">{formatCurrency(r.balance)}</td>
                  </tr>
                ))}
              </tbody>
              <tfoot>
                <tr>
                  <td colSpan={2}><strong>Totals</strong></td>
                  <td className="text-right"><strong>{formatCurrency(trialBalance?.total_debits)}</strong></td>
                  <td className="text-right"><strong>{formatCurrency(trialBalance?.total_credits)}</strong></td>
                  <td></td>
                </tr>
              </tfoot>
            </table>
          )}
        </>
      )}

      {/* Chart of Accounts Tab */}
      {tab === 'accounts' && (
        <>
          <div className="section-header">
            <h2 className="section-title">Chart of Accounts</h2>
            <RoleGate role="CPA_OWNER">
              <button className="btn btn--primary btn--small" onClick={() => {
                setAccountForm({ account_number: '', account_name: '', account_type: '', sub_type: '' });
                setAccountErrors({});
                setShowAddAccount(true);
              }}>
                Add Account
              </button>
            </RoleGate>
          </div>

          <div className="filter-bar">
            <div className="form-field">
              <select
                className="form-input form-select"
                value={accountTypeFilter}
                onChange={(e) => setAccountTypeFilter(e.target.value)}
              >
                {ACCOUNT_TYPES.map((t) => (
                  <option key={t.value} value={t.value}>{t.label}</option>
                ))}
              </select>
            </div>
          </div>

          <DataTable
            columns={[
              { key: 'account_number', label: 'Number' },
              { key: 'account_name', label: 'Name' },
              { key: 'account_type', label: 'Type' },
              { key: 'sub_type', label: 'Sub-Type' },
              { key: 'is_active', label: 'Status', render: (v) => <StatusBadge status={v ? 'ACTIVE' : 'ARCHIVED'} /> },
            ]}
            data={accounts}
            total={accounts.length}
            emptyMessage="No accounts. Clone template accounts to get started."
          />

          <Modal isOpen={showAddAccount} onClose={() => setShowAddAccount(false)} title="Add Account" size="md">
            <form onSubmit={handleAddAccount}>
              <div className="form-row">
                <FormField label="Account Number" error={accountErrors.account_number}>
                  <input className="form-input" value={accountForm.account_number}
                    onChange={(e) => setAccountForm({ ...accountForm, account_number: e.target.value })} autoFocus />
                </FormField>
                <SelectField
                  label="Type" name="account_type" value={accountForm.account_type}
                  onChange={(e) => setAccountForm({ ...accountForm, account_type: e.target.value })}
                  options={ACCOUNT_TYPES.filter((t) => t.value)} placeholder="Select..."
                  error={accountErrors.account_type}
                />
              </div>
              <FormField label="Account Name" error={accountErrors.account_name}>
                <input className="form-input" value={accountForm.account_name}
                  onChange={(e) => setAccountForm({ ...accountForm, account_name: e.target.value })} />
              </FormField>
              <FormField label="Sub-Type (optional)">
                <input className="form-input" value={accountForm.sub_type}
                  onChange={(e) => setAccountForm({ ...accountForm, sub_type: e.target.value })} />
              </FormField>
              <div className="form-actions">
                <button type="button" className="btn btn--outline" onClick={() => setShowAddAccount(false)}>Cancel</button>
                <button type="submit" className="btn btn--primary" disabled={createAccountMutation.isPending}>Create</button>
              </div>
            </form>
          </Modal>
        </>
      )}

      {/* Journal Entries Tab */}
      {tab === 'journal' && (
        <>
          <div className="section-header">
            <h2 className="section-title">Journal Entries</h2>
            <button className="btn btn--primary btn--small" onClick={() => navigate(`/clients/${clientId}/journal-entries/new`)}>
              New Entry
            </button>
          </div>

          <div className="filter-bar">
            <div className="form-field">
              <select
                className="form-input form-select"
                value={jeStatus}
                onChange={(e) => { setJeStatus(e.target.value); setJePage(0); }}
              >
                {JE_STATUSES.map((s) => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          <DataTable
            columns={[
              { key: 'entry_date', label: 'Date', render: (v) => formatDate(v) },
              { key: 'description', label: 'Description' },
              { key: 'reference_number', label: 'Reference' },
              { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
            ]}
            data={journalEntries}
            total={jeData?.total || 0}
            page={jePage}
            pageSize={25}
            onPageChange={setJePage}
            emptyMessage="No journal entries."
          />
        </>
      )}
    </div>
  );
}
