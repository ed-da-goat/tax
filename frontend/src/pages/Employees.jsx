import { useState, useEffect, useCallback } from 'react';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import ClientSelector from '../components/ClientSelector';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import { FormField, SelectField } from '../components/FormField';
import { formatCurrency, formatDate } from '../utils/format';

const PAY_TYPES = [
  { value: 'HOURLY', label: 'Hourly' },
  { value: 'SALARY', label: 'Salary' },
];

const FILING_STATUSES = [
  { value: 'SINGLE', label: 'Single' },
  { value: 'MARRIED', label: 'Married' },
  { value: 'HEAD_OF_HOUSEHOLD', label: 'Head of Household' },
];

const EMPTY_FORM = {
  first_name: '',
  last_name: '',
  filing_status: 'SINGLE',
  allowances: '0',
  pay_rate: '',
  pay_type: 'HOURLY',
  hire_date: new Date().toISOString().slice(0, 10),
};

export default function Employees() {
  const api = useApi();
  const { isCpaOwner } = useAuth();
  const [clientId, setClientId] = useState('');
  const [employees, setEmployees] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [activeOnly, setActiveOnly] = useState(true);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [showEdit, setShowEdit] = useState(null);
  const [form, setForm] = useState(EMPTY_FORM);
  const [confirm, setConfirm] = useState(null);
  const [terminateTarget, setTerminateTarget] = useState(null);
  const [terminateDate, setTerminateDate] = useState('');

  const fetchEmployees = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const params = { skip: page * 25, limit: 25, active_only: activeOnly };
      const res = await api.get(`/api/v1/clients/${clientId}/employees`, { params });
      setEmployees(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch { /* ignore */ }
    setLoading(false);
  }, [clientId, page, activeOnly, api]);

  useEffect(() => { fetchEmployees(); }, [fetchEmployees]);

  const handleCreate = async () => {
    setError('');
    try {
      await api.post(`/api/v1/clients/${clientId}/employees`, {
        ...form,
        allowances: parseInt(form.allowances) || 0,
        pay_rate: parseFloat(form.pay_rate) || 0,
      });
      setShowCreate(false);
      setForm(EMPTY_FORM);
      fetchEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create employee');
    }
  };

  const handleEdit = async () => {
    if (!showEdit) return;
    setError('');
    try {
      await api.patch(`/api/v1/clients/${clientId}/employees/${showEdit}`, {
        ...form,
        allowances: parseInt(form.allowances) || 0,
        pay_rate: parseFloat(form.pay_rate) || 0,
      });
      setShowEdit(null);
      fetchEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to update employee');
    }
  };

  const handleTerminate = async () => {
    if (!terminateTarget) return;
    try {
      await api.post(`/api/v1/clients/${clientId}/employees/${terminateTarget}/terminate`, null, {
        params: { termination_date: terminateDate },
      });
      setTerminateTarget(null);
      fetchEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to terminate employee');
    }
  };

  const handleDelete = async (id) => {
    try {
      await api.delete(`/api/v1/clients/${clientId}/employees/${id}`);
      fetchEmployees();
    } catch (e) {
      setError(e.response?.data?.detail || 'Delete failed');
    }
    setConfirm(null);
  };

  const openEdit = (emp) => {
    setForm({
      first_name: emp.first_name,
      last_name: emp.last_name,
      filing_status: emp.filing_status,
      allowances: String(emp.allowances),
      pay_rate: String(emp.pay_rate),
      pay_type: emp.pay_type,
      hire_date: emp.hire_date,
    });
    setShowEdit(emp.id);
  };

  const columns = [
    { key: 'first_name', label: 'First Name' },
    { key: 'last_name', label: 'Last Name' },
    { key: 'pay_type', label: 'Pay Type' },
    { key: 'pay_rate', label: 'Rate', render: (v, row) => row.pay_type === 'SALARY' ? `${formatCurrency(v)}/yr` : `${formatCurrency(v)}/hr` },
    { key: 'filing_status', label: 'Filing', render: (v) => v?.replace(/_/g, ' ') },
    { key: 'hire_date', label: 'Hired', render: (v) => formatDate(v) },
    { key: 'is_active', label: 'Status', render: (v) => <StatusBadge status={v ? 'ACTIVE' : 'ARCHIVED'} /> },
    {
      key: 'id', label: 'Actions', render: (v, row) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); openEdit(row); }}>Edit</button>
          {row.is_active && isCpaOwner() && (
            <button className="btn btn--small btn--danger" onClick={(e) => { e.stopPropagation(); setTerminateTarget(v); setTerminateDate(new Date().toISOString().slice(0, 10)); }}>Terminate</button>
          )}
        </div>
      ),
    },
  ];

  const formFields = (
    <>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <FormField label="First Name">
          <input className="form-input" value={form.first_name} onChange={(e) => setForm({ ...form, first_name: e.target.value })} />
        </FormField>
        <FormField label="Last Name">
          <input className="form-input" value={form.last_name} onChange={(e) => setForm({ ...form, last_name: e.target.value })} />
        </FormField>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
        <SelectField label="Pay Type" name="pay_type" value={form.pay_type} onChange={(e) => setForm({ ...form, pay_type: e.target.value })} options={PAY_TYPES} />
        <FormField label={form.pay_type === 'SALARY' ? 'Annual Salary' : 'Hourly Rate'}>
          <input className="form-input" type="number" step="0.01" value={form.pay_rate} onChange={(e) => setForm({ ...form, pay_rate: e.target.value })} />
        </FormField>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
        <SelectField label="Filing Status" name="filing_status" value={form.filing_status} onChange={(e) => setForm({ ...form, filing_status: e.target.value })} options={FILING_STATUSES} />
        <FormField label="Allowances">
          <input className="form-input" type="number" min="0" value={form.allowances} onChange={(e) => setForm({ ...form, allowances: e.target.value })} />
        </FormField>
        <FormField label="Hire Date">
          <input className="form-input" type="date" value={form.hire_date} onChange={(e) => setForm({ ...form, hire_date: e.target.value })} />
        </FormField>
      </div>
    </>
  );

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Employees</h1>
        <button className="btn btn--primary" onClick={() => { setForm(EMPTY_FORM); setShowCreate(true); }} disabled={!clientId}>Add Employee</button>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <ClientSelector value={clientId} onSelect={(id) => { setClientId(id); setPage(0); }} />
        <label style={{ fontSize: 13, display: 'flex', alignItems: 'center', gap: 4 }}>
          <input type="checkbox" checked={activeOnly} onChange={(e) => setActiveOnly(e.target.checked)} /> Active only
        </label>
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <DataTable columns={columns} data={employees} total={total} page={page} onPageChange={setPage} loading={loading} emptyMessage="No employees found." />

      {/* Create Modal */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="Add Employee" size="md">
        {formFields}
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowCreate(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleCreate}>Create</button>
        </div>
      </Modal>

      {/* Edit Modal */}
      <Modal isOpen={!!showEdit} onClose={() => setShowEdit(null)} title="Edit Employee" size="md">
        {formFields}
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowEdit(null)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleEdit}>Save</button>
        </div>
      </Modal>

      {/* Terminate Confirm */}
      <Modal isOpen={!!terminateTarget} onClose={() => setTerminateTarget(null)} title="Terminate Employee" size="sm">
        <FormField label="Termination Date">
          <input className="form-input" type="date" value={terminateDate} onChange={(e) => setTerminateDate(e.target.value)} />
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setTerminateTarget(null)}>Cancel</button>
          <button className="btn btn--danger" onClick={handleTerminate}>Terminate</button>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={!!confirm}
        title="Delete Employee"
        message="Soft-delete this employee record?"
        confirmLabel="Delete"
        onConfirm={() => handleDelete(confirm.id)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
