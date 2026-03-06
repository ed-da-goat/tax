import { useState, useRef } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatDate } from '../utils/format';

const WORKFLOW_TYPES = ['Tax Prep', 'Bookkeeping', 'Payroll', 'Onboarding', 'Advisory'];
const STATUS_COLORS = {
  ACTIVE: '#3d6d8e', COMPLETED: '#10B981', TEMPLATE: '#6B7280', ARCHIVED: '#9CA3AF',
};
const PRIORITY_COLORS = {
  LOW: '#9CA3AF', MEDIUM: '#3d6d8e', HIGH: '#F59E0B', URGENT: '#EF4444',
};
const TASK_STATUS_COLORS = {
  NOT_STARTED: '#9CA3AF', IN_PROGRESS: '#3d6d8e', WAITING_CLIENT: '#F59E0B',
  IN_REVIEW: '#8B5CF6', COMPLETED: '#10B981', BLOCKED: '#EF4444',
};

export default function Workflows() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [viewType, setViewType] = useState('list');
  const [selectedType, setSelectedType] = useState('Tax Prep');
  const [filters, setFilters] = useState({ status: 'ACTIVE', is_template: false });
  const dragItem = useRef(null);
  const dragOverCol = useRef(null);

  const params = new URLSearchParams();
  if (filters.status) params.set('status', filters.status);
  params.set('is_template', filters.is_template);

  const { data: workflows, refetch } = useApiQuery(['workflows', filters], `/api/v1/workflows?${params}`);
  const { data: kanban, refetch: refetchKanban } = useApiQuery(['kanban', selectedType], `/api/v1/kanban/${encodeURIComponent(selectedType)}`, { enabled: viewType === 'kanban' });
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

  function handleDragStart(e, wf) {
    dragItem.current = wf;
    e.dataTransfer.effectAllowed = 'move';
    e.currentTarget.style.opacity = '0.5';
  }

  function handleDragEnd(e) {
    e.currentTarget.style.opacity = '1';
    dragItem.current = null;
    dragOverCol.current = null;
  }

  function handleDragOver(e, stageName) {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    dragOverCol.current = stageName;
  }

  async function handleDrop(e, stageName) {
    e.preventDefault();
    if (dragItem.current && dragItem.current.current_stage !== stageName) {
      await handleStageChange(dragItem.current.id, stageName);
      refetchKanban();
    }
    dragItem.current = null;
    dragOverCol.current = null;
  }

  const items = workflows?.items || [];
  const clientList = clients?.items || [];

  function getClientName(cid) {
    return clientList.find(c => c.id === cid)?.name || '';
  }

  function isDueOverdue(dueDate) {
    return dueDate && new Date(dueDate) < new Date();
  }

  const columns = [
    { key: 'name', label: 'Workflow', render: (row) => (
      <div>
        <div style={{ fontWeight: 500 }}>{row.name}</div>
        {row.description && <div style={{ fontSize: '12px', color: '#6B7280', marginTop: '2px' }}>{row.description}</div>}
      </div>
    )},
    { key: 'workflow_type', label: 'Type' },
    { key: 'client', label: 'Client', render: (row) => getClientName(row.client_id) || '—' },
    { key: 'current_stage', label: 'Stage', render: (row) => (
      <select value={row.current_stage} onChange={e => handleStageChange(row.id, e.target.value)} className="inline-select">
        {(stages || []).map(s => <option key={s.stage_name} value={s.stage_name}>{s.stage_name}</option>)}
      </select>
    )},
    { key: 'due_date', label: 'Due', render: (row) => row.due_date ? (
      <span style={{ color: isDueOverdue(row.due_date) ? '#EF4444' : 'inherit', fontWeight: isDueOverdue(row.due_date) ? 600 : 400 }}>
        {formatDate(row.due_date)}
      </span>
    ) : '—' },
    { key: 'tasks', label: 'Progress', render: (row) => {
      const tasks = row.tasks || [];
      const done = tasks.filter(t => t.status === 'COMPLETED').length;
      const total = tasks.length;
      const pct = total > 0 ? Math.round((done / total) * 100) : 0;
      return total > 0 ? (
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ flex: 1, height: '6px', backgroundColor: '#E5E7EB', borderRadius: '3px', minWidth: '60px' }}>
            <div style={{ width: `${pct}%`, height: '100%', backgroundColor: pct === 100 ? '#10B981' : '#3d6d8e', borderRadius: '3px', transition: 'width 0.3s' }} />
          </div>
          <span style={{ fontSize: '12px', color: '#6B7280', whiteSpace: 'nowrap' }}>{done}/{total}</span>
        </div>
      ) : '—';
    }},
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
          <select value={selectedType} onChange={e => setSelectedType(e.target.value)} style={{ padding: '6px 12px', borderRadius: '6px', border: '1px solid #D1D5DB' }}>
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
        <div style={{ display: 'flex', gap: '12px', overflowX: 'auto', paddingBottom: '16px', minHeight: '400px' }}>
          {(kanban || []).map(col => (
            <div
              key={col.stage_name}
              onDragOver={e => handleDragOver(e, col.stage_name)}
              onDrop={e => handleDrop(e, col.stage_name)}
              style={{
                minWidth: '280px', maxWidth: '320px', flex: '1 0 280px',
                backgroundColor: '#f3f4f6', borderRadius: '8px', padding: '12px',
                border: '2px solid transparent',
                transition: 'border-color 0.2s',
              }}
            >
              {/* Column header */}
              <div style={{
                display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                marginBottom: '12px', paddingBottom: '8px', borderBottom: `3px solid ${col.color || '#6B7280'}`,
              }}>
                <h3 style={{ fontSize: '14px', fontWeight: 600, margin: 0, color: '#374151' }}>
                  {col.stage_name}
                </h3>
                <span style={{
                  display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
                  width: '24px', height: '24px', borderRadius: '12px',
                  backgroundColor: col.color || '#6B7280', color: 'white',
                  fontSize: '12px', fontWeight: 600,
                }}>
                  {col.count || col.workflows?.length || 0}
                </span>
              </div>

              {/* Cards */}
              {(col.workflows || []).map(wf => {
                const tasks = wf.tasks || [];
                const done = tasks.filter(t => t.status === 'COMPLETED').length;
                const total = tasks.length;
                const overdue = isDueOverdue(wf.due_date);

                return (
                  <div
                    key={wf.id}
                    draggable
                    onDragStart={e => handleDragStart(e, wf)}
                    onDragEnd={handleDragEnd}
                    style={{
                      backgroundColor: 'white', borderRadius: '8px', padding: '12px',
                      marginBottom: '8px', boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
                      cursor: 'grab', borderLeft: `4px solid ${overdue ? '#EF4444' : col.color || '#6B7280'}`,
                      transition: 'box-shadow 0.2s',
                    }}
                    onMouseEnter={e => e.currentTarget.style.boxShadow = '0 4px 8px rgba(0,0,0,0.12)'}
                    onMouseLeave={e => e.currentTarget.style.boxShadow = '0 1px 3px rgba(0,0,0,0.08)'}
                  >
                    {/* Card title */}
                    <div style={{ fontWeight: 600, fontSize: '14px', color: '#111827', marginBottom: '6px' }}>
                      {wf.name}
                    </div>

                    {/* Client name */}
                    {wf.client_id && (
                      <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '6px' }}>
                        {getClientName(wf.client_id)}
                      </div>
                    )}

                    {/* Task progress bar */}
                    {total > 0 && (
                      <div style={{ marginBottom: '8px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '4px' }}>
                          <span style={{ fontSize: '11px', color: '#9CA3AF' }}>Tasks</span>
                          <span style={{ fontSize: '11px', color: '#6B7280' }}>{done}/{total}</span>
                        </div>
                        <div style={{ height: '4px', backgroundColor: '#E5E7EB', borderRadius: '2px' }}>
                          <div style={{
                            width: `${total > 0 ? (done / total) * 100 : 0}%`,
                            height: '100%',
                            backgroundColor: done === total ? '#10B981' : '#3d6d8e',
                            borderRadius: '2px', transition: 'width 0.3s',
                          }} />
                        </div>
                      </div>
                    )}

                    {/* Footer: due date + assignee */}
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      {wf.due_date ? (
                        <div style={{
                          fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px',
                          color: overdue ? '#EF4444' : '#6B7280',
                          fontWeight: overdue ? 600 : 400,
                        }}>
                          <span style={{ fontSize: '14px' }}>{overdue ? '\u26A0' : '\uD83D\uDCC5'}</span>
                          {formatDate(wf.due_date)}
                        </div>
                      ) : <div />}
                      {wf.assigned_to && (
                        <div style={{
                          width: '28px', height: '28px', borderRadius: '14px',
                          backgroundColor: '#E5E7EB', display: 'flex', alignItems: 'center',
                          justifyContent: 'center', fontSize: '11px', fontWeight: 600, color: '#4B5563',
                        }}>
                          {wf.assigned_name ? wf.assigned_name.split(' ').map(n => n[0]).join('') : 'U'}
                        </div>
                      )}
                    </div>
                  </div>
                );
              })}

              {/* Empty column placeholder */}
              {(!col.workflows || col.workflows.length === 0) && (
                <div style={{ padding: '20px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px', border: '2px dashed #E5E7EB', borderRadius: '6px' }}>
                  No items
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <Modal isOpen={showAdd} title="New Workflow" onClose={() => setShowAdd(false)}>
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
            <button type="submit" className="btn btn--primary" disabled={addWorkflow.isPending}>
              {addWorkflow.isPending ? 'Creating...' : 'Create'}
            </button>
          </div>
        </form>
      </Modal>
      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
