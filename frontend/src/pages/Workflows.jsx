import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatDate } from '../utils/format';

const WORKFLOW_TYPES = ['Tax Prep', 'Bookkeeping', 'Payroll', 'Onboarding', 'Advisory'];
const STATUS_COLORS = {
  ACTIVE: '#3B82F6', COMPLETED: '#10B981', TEMPLATE: '#6B7280', ARCHIVED: '#9CA3AF',
};

export default function Workflows() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [viewType, setViewType] = useState('list'); // 'list' or 'kanban'
  const [selectedType, setSelectedType] = useState('Tax Prep');
  const [filters, setFilters] = useState({ status: 'ACTIVE', is_template: false });

  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  params.set('is_template', filters.is_template);

  const { data: workflows } = useApiQuery(['workflows', filters], `/api/v1/workflows?${params}`);
  const { data: kanban } = useApiQuery(['kanban', selectedType], `/api/v1/kanban/${encodeURIComponent(selectedType)}`, { enabled: viewType === 'kanban' });
  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const { data: stages } = useApiQuery(['stages', selectedType], `/api/v1/stages/${encodeURIComponent(selectedType)}`);

  const addWorkflow = useApiMutation('post', '/api/v1/workflows', { invalidate: [['workflows'], ['kanban']] });
  const updateWorkflow = useApiMutation('put', (body) => `/api/v1/workflows/${body.id}`, { invalidate: [['workflows'], ['kanban']] });

  const [form, setForm] = useState({ name: '', workflow_type: 'Tax Prep', client_id: '', due_date: '', description: '' });

  async function handleAdd(e) {
    e.preventDefault();
    try {
      await addWorkflow.mutateAsync({ ...form, client_id: form.client_id || null });
      setShowAdd(false);
      setForm({ name: '', workflow_type: 'Tax Prep', client_id: '', due_date: '', description: '' });
      setToast({ type: 'success', message: 'Workflow created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handleStageChange(workflowId, newStage) {
    try {
      await updateWorkflow.mutateAsync({ id: workflowId, current_stage: newStage });
    } catch (err) { setToast({ type: 'error', message: 'Failed to update stage' }); }
  }

  const items = workflows?.items || [];
  const clientList = clients?.items || [];

  const columns = [
    { key: 'name', label: 'Workflow' },
    { key: 'workflow_type', label: 'Type' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'current_stage', label: 'Stage', render: (row) => (
      <select value={row.current_stage} onChange={e => handleStageChange(row.id, e.target.value)} className="inline-select">
        {(stages || []).map(s => <option key={s.stage_name} value={s.stage_name}>{s.stage_name}</option>)}
      </select>
    )},
    { key: 'due_date', label: 'Due', render: (row) => row.due_date ? formatDate(row.due_date) : '—' },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Workflows</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          <button className={`btn ${viewType === 'list' ? 'btn--primary' : 'btn--outline'}`} onClick={() => setViewType('list')}>List</button>
          <button className={`btn ${viewType === 'kanban' ? 'btn--primary' : 'btn--outline'}`} onClick={() => setViewType('kanban')}>Kanban</button>
          <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ New Workflow</button>
        </div>
      </div>

      {viewType === 'kanban' && (
        <div style={{ marginBottom: '16px' }}>
          <select value={selectedType} onChange={e => setSelectedType(e.target.value)}>
            {WORKFLOW_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
          </select>
        </div>
      )}

      {viewType === 'list' ? (
        <>
          <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
            <select value={filters.status} onChange={e => setFilters(f => ({ ...f, status: e.target.value }))}>
              <option value="">All</option>
              <option value="ACTIVE">Active</option>
              <option value="COMPLETED">Completed</option>
              <option value="TEMPLATE">Templates</option>
            </select>
          </div>
          <DataTable columns={columns} rows={items} emptyMessage="No workflows found" />
        </>
      ) : (
        <div style={{ display: 'flex', gap: '16px', overflowX: 'auto', paddingBottom: '16px' }}>
          {(kanban || []).map(col => (
            <div key={col.stage_name} style={{ minWidth: '250px', backgroundColor: '#f9fafb', borderRadius: '8px', padding: '12px' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '12px' }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600 }}>{col.stage_name}</h3>
                <span className="badge" style={{ backgroundColor: col.color }}>{col.count}</span>
              </div>
              {col.workflows.map(wf => (
                <div key={wf.id} style={{ backgroundColor: 'white', borderRadius: '6px', padding: '10px', marginBottom: '8px', boxShadow: '0 1px 2px rgba(0,0,0,0.05)' }}>
                  <div style={{ fontWeight: 500, fontSize: '14px' }}>{wf.name}</div>
                  <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '4px' }}>
                    {clientList.find(c => c.id === wf.client_id)?.name || ''}
                  </div>
                  {wf.due_date && (
                    <div style={{ fontSize: '12px', color: new Date(wf.due_date) < new Date() ? '#EF4444' : '#6B7280', marginTop: '4px' }}>
                      Due: {formatDate(wf.due_date)}
                    </div>
                  )}
                </div>
              ))}
            </div>
          ))}
        </div>
      )}

      {showAdd && (
        <Modal title="New Workflow" onClose={() => setShowAdd(false)}>
          <form onSubmit={handleAdd}>
            <FormField label="Name" required>
              <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
            </FormField>
            <FormField label="Type" required>
              <select value={form.workflow_type} onChange={e => setForm(f => ({ ...f, workflow_type: e.target.value }))}>
                {WORKFLOW_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </FormField>
            <FormField label="Client">
              <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))}>
                <option value="">All clients / None</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <FormField label="Due Date">
              <input type="date" value={form.due_date} onChange={e => setForm(f => ({ ...f, due_date: e.target.value }))} />
            </FormField>
            <FormField label="Description">
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={addWorkflow.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
