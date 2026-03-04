import { useState, useEffect, useCallback } from 'react';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import ClientSelector from '../components/ClientSelector';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import Tabs from '../components/Tabs';
import { formatCurrency, formatDate } from '../utils/format';

const TABS = [
  { key: 'accounts', label: 'Bank Accounts' },
  { key: 'transactions', label: 'Transactions' },
  { key: 'reconciliations', label: 'Reconciliations' },
];

export default function BankReconciliation() {
  const api = useApi();
  const { isCpaOwner } = useAuth();
  const [clientId, setClientId] = useState('');
  const [tab, setTab] = useState('accounts');

  // Bank accounts
  const [bankAccounts, setBankAccounts] = useState([]);
  const [selectedAccount, setSelectedAccount] = useState(null);
  const [showCreateAccount, setShowCreateAccount] = useState(false);
  const [accountForm, setAccountForm] = useState({ account_name: '', institution_name: '' });

  // Transactions
  const [transactions, setTransactions] = useState([]);
  const [txTotal, setTxTotal] = useState(0);
  const [txPage, setTxPage] = useState(0);

  // Reconciliations
  const [reconciliations, setReconciliations] = useState([]);
  const [showCreateRecon, setShowCreateRecon] = useState(false);
  const [reconForm, setReconForm] = useState({ statement_date: '', statement_balance: '' });

  // Import
  const [showImport, setShowImport] = useState(false);
  const [importText, setImportText] = useState('');

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [confirm, setConfirm] = useState(null);

  const fetchAccounts = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/bank-accounts`);
      setBankAccounts(res.data.items || []);
      if (!selectedAccount && (res.data.items || []).length > 0) {
        setSelectedAccount(res.data.items[0].id);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [clientId, api]);

  const fetchTransactions = useCallback(async () => {
    if (!clientId || !selectedAccount) return;
    setLoading(true);
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/bank-accounts/${selectedAccount}/transactions`, {
        params: { skip: txPage * 25, limit: 25 },
      });
      setTransactions(res.data.items || []);
      setTxTotal(res.data.total || 0);
    } catch { /* ignore */ }
    setLoading(false);
  }, [clientId, selectedAccount, txPage, api]);

  const fetchReconciliations = useCallback(async () => {
    if (!clientId || !selectedAccount) return;
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/bank-accounts/${selectedAccount}/reconciliations`);
      setReconciliations(res.data.items || []);
    } catch { /* ignore */ }
  }, [clientId, selectedAccount, api]);

  useEffect(() => { fetchAccounts(); }, [fetchAccounts]);
  useEffect(() => { if (tab === 'transactions') fetchTransactions(); }, [tab, fetchTransactions]);
  useEffect(() => { if (tab === 'reconciliations') fetchReconciliations(); }, [tab, fetchReconciliations]);

  const handleCreateAccount = async () => {
    setError('');
    try {
      await api.post(`/api/v1/clients/${clientId}/bank-accounts`, accountForm);
      setShowCreateAccount(false);
      setAccountForm({ account_name: '', institution_name: '' });
      fetchAccounts();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create account');
    }
  };

  const handleImport = async () => {
    setError('');
    try {
      const lines = importText.trim().split('\n').filter(Boolean);
      const txns = lines.map((line) => {
        const parts = line.split(',');
        return {
          transaction_date: parts[0]?.trim(),
          description: parts[1]?.trim() || null,
          amount: parseFloat(parts[2]?.trim()) || 0,
          transaction_type: (parts[3]?.trim() || 'DEBIT').toUpperCase(),
        };
      });
      await api.post(`/api/v1/clients/${clientId}/bank-accounts/${selectedAccount}/transactions/import`, { transactions: txns });
      setShowImport(false);
      setImportText('');
      fetchTransactions();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to import transactions');
    }
  };

  const handleCreateRecon = async () => {
    setError('');
    try {
      await api.post(`/api/v1/clients/${clientId}/bank-accounts/${selectedAccount}/reconciliations`, {
        statement_date: reconForm.statement_date,
        statement_balance: parseFloat(reconForm.statement_balance),
      });
      setShowCreateRecon(false);
      setReconForm({ statement_date: '', statement_balance: '' });
      fetchReconciliations();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create reconciliation');
    }
  };

  const handleComplete = async (reconId) => {
    try {
      await api.post(`/api/v1/clients/${clientId}/bank-accounts/${selectedAccount}/reconciliations/${reconId}/complete`);
      fetchReconciliations();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to complete reconciliation');
    }
    setConfirm(null);
  };

  const accountColumns = [
    { key: 'account_name', label: 'Account Name' },
    { key: 'institution_name', label: 'Institution', render: (v) => v || '--' },
  ];

  const txColumns = [
    { key: 'transaction_date', label: 'Date', render: (v) => formatDate(v) },
    { key: 'description', label: 'Description', render: (v) => v || '--' },
    { key: 'amount', label: 'Amount', render: (v) => formatCurrency(v) },
    { key: 'transaction_type', label: 'Type' },
    { key: 'is_reconciled', label: 'Reconciled', render: (v) => v ? 'Yes' : 'No' },
  ];

  const reconColumns = [
    { key: 'statement_date', label: 'Statement Date', render: (v) => formatDate(v) },
    { key: 'statement_balance', label: 'Statement Balance', render: (v) => formatCurrency(v) },
    { key: 'reconciled_balance', label: 'Reconciled Balance', render: (v) => formatCurrency(v) },
    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
    {
      key: 'id', label: 'Actions', render: (v, row) =>
        row.status === 'IN_PROGRESS' && isCpaOwner() ? (
          <button className="btn btn--small btn--primary" onClick={(e) => { e.stopPropagation(); setConfirm({ id: v, msg: 'Complete this reconciliation?' }); }}>
            Complete
          </button>
        ) : null,
    },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Bank Reconciliation</h1>
      </div>

      <ClientSelector value={clientId} onSelect={(id) => { setClientId(id); setSelectedAccount(null); }} />

      {error && <div className="alert alert--error">{error}</div>}

      {bankAccounts.length > 0 && (
        <div style={{ marginBottom: 16, display: 'flex', gap: 12, alignItems: 'center' }}>
          <label style={{ fontWeight: 600, fontSize: 13 }}>Bank Account:</label>
          <select className="form-input form-select" style={{ maxWidth: 260, marginBottom: 0 }} value={selectedAccount || ''} onChange={(e) => setSelectedAccount(e.target.value)}>
            {bankAccounts.map((a) => <option key={a.id} value={a.id}>{a.account_name}</option>)}
          </select>
        </div>
      )}

      <Tabs tabs={TABS} activeTab={tab} onTabChange={setTab} />

      <div style={{ marginTop: 16 }}>
        {tab === 'accounts' && (
          <>
            <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={() => setShowCreateAccount(true)} disabled={!clientId}>Add Bank Account</button>
            <DataTable columns={accountColumns} data={bankAccounts} total={bankAccounts.length} loading={loading} emptyMessage="No bank accounts." onRowClick={(row) => { setSelectedAccount(row.id); setTab('transactions'); }} />
          </>
        )}

        {tab === 'transactions' && (
          <>
            <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
              <button className="btn btn--primary" onClick={() => setShowImport(true)} disabled={!selectedAccount}>Import Transactions</button>
            </div>
            <DataTable columns={txColumns} data={transactions} total={txTotal} page={txPage} onPageChange={setTxPage} loading={loading} emptyMessage="No transactions." />
          </>
        )}

        {tab === 'reconciliations' && (
          <>
            <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={() => setShowCreateRecon(true)} disabled={!selectedAccount}>New Reconciliation</button>
            <DataTable columns={reconColumns} data={reconciliations} total={reconciliations.length} loading={loading} emptyMessage="No reconciliations." />
          </>
        )}
      </div>

      {/* Create Bank Account */}
      <Modal isOpen={showCreateAccount} onClose={() => setShowCreateAccount(false)} title="Add Bank Account" size="sm">
        <FormField label="Account Name">
          <input className="form-input" value={accountForm.account_name} onChange={(e) => setAccountForm({ ...accountForm, account_name: e.target.value })} />
        </FormField>
        <FormField label="Institution (optional)">
          <input className="form-input" value={accountForm.institution_name} onChange={(e) => setAccountForm({ ...accountForm, institution_name: e.target.value })} />
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowCreateAccount(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleCreateAccount}>Create</button>
        </div>
      </Modal>

      {/* Import Transactions */}
      <Modal isOpen={showImport} onClose={() => setShowImport(false)} title="Import Bank Transactions" size="md">
        <p style={{ marginBottom: 12, fontSize: 13, color: 'var(--color-text-muted)' }}>
          Paste CSV data: date, description, amount, type (DEBIT/CREDIT). One transaction per line.
        </p>
        <textarea className="form-input" rows={8} value={importText} onChange={(e) => setImportText(e.target.value)} placeholder="2024-01-15, Office Supplies, 45.99, DEBIT" />
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowImport(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleImport}>Import</button>
        </div>
      </Modal>

      {/* Create Reconciliation */}
      <Modal isOpen={showCreateRecon} onClose={() => setShowCreateRecon(false)} title="New Reconciliation" size="sm">
        <FormField label="Statement Date">
          <input className="form-input" type="date" value={reconForm.statement_date} onChange={(e) => setReconForm({ ...reconForm, statement_date: e.target.value })} />
        </FormField>
        <FormField label="Statement Balance">
          <input className="form-input" type="number" step="0.01" value={reconForm.statement_balance} onChange={(e) => setReconForm({ ...reconForm, statement_balance: e.target.value })} />
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowCreateRecon(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleCreateRecon}>Create</button>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={!!confirm}
        title="Complete Reconciliation"
        message={confirm?.msg}
        confirmLabel="Complete"
        confirmVariant="primary"
        onConfirm={() => handleComplete(confirm.id)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
