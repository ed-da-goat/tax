import { useState } from 'react';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import useAuth from '../hooks/useAuth';
import RoleGate from '../components/RoleGate';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField, SelectField } from '../components/FormField';
import ClientSelector from '../components/ClientSelector';
import { useApiQuery } from '../hooks/useApiQuery';

const FREQUENCIES = [
  { value: 'WEEKLY', label: 'Weekly' },
  { value: 'BIWEEKLY', label: 'Biweekly' },
  { value: 'MONTHLY', label: 'Monthly' },
  { value: 'QUARTERLY', label: 'Quarterly' },
  { value: 'ANNUALLY', label: 'Annually' },
];

export default function RecurringTransactions() {
  const api = useApi();
  const { addToast } = useToast();
  const { isCpaOwner } = useAuth();

  const [clientId, setClientId] = useState('');
  const [templates, setTemplates] = useState([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [saving, setSaving] = useState(false);
  const [generating, setGenerating] = useState(false);

  const [form, setForm] = useState({
    source_type: 'JOURNAL_ENTRY',
    description: '',
    frequency: 'MONTHLY',
    next_date: '',
    end_date: '',
    lines: [
      { account_id: '', description: '', debit: '', credit: '' },
      { account_id: '', description: '', debit: '', credit: '' },
    ],
  });

  const { data: accountsData } = useApiQuery(
    ['accounts', clientId],
    `/api/v1/clients/${clientId}/accounts`,
    { enabled: !!clientId }
  );
  const accounts = (accountsData?.items || []).filter((a) => a.is_active);

  const fetchTemplates = async (cid) => {
    if (!cid) return;
    setLoading(true);
    try {
      const res = await api.get(`/api/v1/clients/${cid}/recurring`);
      setTemplates(res.data);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to load templates');
    }
    setLoading(false);
  };

  const handleClientChange = (cid) => {
    setClientId(cid);
    fetchTemplates(cid);
  };

  const openCreate = () => {
    setEditingId(null);
    setForm({
      source_type: 'JOURNAL_ENTRY',
      description: '',
      frequency: 'MONTHLY',
      next_date: '',
      end_date: '',
      lines: [
        { account_id: '', description: '', debit: '', credit: '' },
        { account_id: '', description: '', debit: '', credit: '' },
      ],
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const body = {
        ...form,
        end_date: form.end_date || null,
        lines: form.lines.filter((l) => l.account_id).map((l) => ({
          account_id: l.account_id,
          description: l.description || null,
          debit: parseFloat(l.debit) || 0,
          credit: parseFloat(l.credit) || 0,
        })),
      };
      if (editingId) {
        const { lines, source_type, ...updateBody } = body;
        await api.patch(`/api/v1/clients/${clientId}/recurring/${editingId}`, updateBody);
        addToast('success', 'Template updated');
      } else {
        await api.post(`/api/v1/clients/${clientId}/recurring`, body);
        addToast('success', 'Template created');
      }
      setModalOpen(false);
      fetchTemplates(clientId);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to save template');
    }
    setSaving(false);
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/v1/clients/${clientId}/recurring/${id}`);
      addToast('success', 'Template deleted');
      fetchTemplates(clientId);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to delete');
    }
  };

  const handleGenerate = async () => {
    setGenerating(true);
    try {
      const res = await api.post('/api/v1/recurring/generate');
      addToast('success', `Generated ${res.data.generated || 0} transactions`);
      if (clientId) fetchTemplates(clientId);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Generation failed');
    }
    setGenerating(false);
  };

  const updateLine = (idx, field, value) => {
    const updated = [...form.lines];
    updated[idx] = { ...updated[idx], [field]: value };
    setForm({ ...form, lines: updated });
  };

  const columns = [
    { key: 'description', label: 'Description' },
    { key: 'source_type', label: 'Type' },
    { key: 'frequency', label: 'Frequency' },
    { key: 'next_date', label: 'Next Date' },
    {
      key: 'status',
      label: 'Status',
      render: (val) => (
        <span className={`badge badge--${(val || 'active').toLowerCase()}`}>{val || 'ACTIVE'}</span>
      ),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
          <button className="btn btn--small btn--outline" onClick={() => {
            setEditingId(row.id);
            setForm({
              source_type: row.source_type,
              description: row.description || '',
              frequency: row.frequency,
              next_date: row.next_date || '',
              end_date: row.end_date || '',
              lines: [],
            });
            setModalOpen(true);
          }}>
            Edit
          </button>
          <button className="btn btn--small btn--danger" onClick={() => handleDelete(row.id)}>
            Delete
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      <div className="page-header">
        <h1 className="page-title">Recurring Transactions</h1>
        <div style={{ display: 'flex', gap: 8 }}>
          {isCpaOwner && (
            <button
              className={`btn btn--outline${generating ? ' btn--loading' : ''}`}
              onClick={handleGenerate}
              disabled={generating}
            >
              Generate Due
            </button>
          )}
        </div>
      </div>

      <div className="card mb-24" style={{ padding: 16 }}>
        <div style={{ maxWidth: 320 }}>
          <ClientSelector value={clientId} onChange={handleClientChange} />
        </div>
      </div>

      {clientId && (
        <>
          <div style={{ marginBottom: 16 }}>
            <button className="btn btn--primary" onClick={openCreate}>
              Add Template
            </button>
          </div>

          <DataTable
            columns={columns}
            data={templates}
            total={templates.length}
            loading={loading}
            emptyMessage="No recurring templates for this client."
          />
        </>
      )}

      <Modal
        isOpen={modalOpen}
        title={editingId ? 'Edit Template' : 'Create Template'}
        onClose={() => !saving && setModalOpen(false)}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <FormField label="Description">
            <input
              className="form-input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </FormField>
          <div className="form-row">
            <SelectField
              label="Type"
              value={form.source_type}
              onChange={(e) => setForm({ ...form, source_type: e.target.value })}
              options={[
                { value: 'JOURNAL_ENTRY', label: 'Journal Entry' },
                { value: 'BILL', label: 'Bill' },
              ]}
            />
            <SelectField
              label="Frequency"
              value={form.frequency}
              onChange={(e) => setForm({ ...form, frequency: e.target.value })}
              options={FREQUENCIES}
            />
          </div>
          <div className="form-row">
            <FormField label="Next Date">
              <input
                className="form-input"
                type="date"
                value={form.next_date}
                onChange={(e) => setForm({ ...form, next_date: e.target.value })}
              />
            </FormField>
            <FormField label="End Date (optional)">
              <input
                className="form-input"
                type="date"
                value={form.end_date}
                onChange={(e) => setForm({ ...form, end_date: e.target.value })}
              />
            </FormField>
          </div>

          {!editingId && (
            <>
              <h3 style={{ fontSize: 14, fontWeight: 600, marginTop: 8 }}>Line Items</h3>
              {form.lines.map((line, i) => (
                <div key={i} className="form-row">
                  <FormField label="Account">
                    <select
                      className="form-input form-select"
                      value={line.account_id}
                      onChange={(e) => updateLine(i, 'account_id', e.target.value)}
                    >
                      <option value="">Select...</option>
                      {accounts.map((a) => (
                        <option key={a.id} value={a.id}>{a.account_number} - {a.account_name}</option>
                      ))}
                    </select>
                  </FormField>
                  <FormField label="Debit">
                    <input className="form-input" type="number" step="0.01" value={line.debit}
                      onChange={(e) => updateLine(i, 'debit', e.target.value)} placeholder="0.00" />
                  </FormField>
                  <FormField label="Credit">
                    <input className="form-input" type="number" step="0.01" value={line.credit}
                      onChange={(e) => updateLine(i, 'credit', e.target.value)} placeholder="0.00" />
                  </FormField>
                </div>
              ))}
              <button className="btn btn--small btn--outline"
                onClick={() => setForm({ ...form, lines: [...form.lines, { account_id: '', description: '', debit: '', credit: '' }] })}>
                Add Line
              </button>
            </>
          )}
        </div>
        <div className="modal-actions" style={{ marginTop: 16 }}>
          <button className="btn btn--outline" onClick={() => setModalOpen(false)} disabled={saving}>Cancel</button>
          <button className={`btn btn--primary${saving ? ' btn--loading' : ''}`} onClick={handleSave} disabled={saving}>
            {editingId ? 'Save Changes' : 'Create Template'}
          </button>
        </div>
      </Modal>
    </div>
  );
}
