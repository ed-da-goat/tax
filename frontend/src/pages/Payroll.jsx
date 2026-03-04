import { useState, useEffect, useCallback } from 'react';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import ClientSelector from '../components/ClientSelector';
import DataTable from '../components/DataTable';
import StatusBadge from '../components/StatusBadge';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import RoleGate from '../components/RoleGate';
import { formatCurrency, formatDate } from '../utils/format';

export default function Payroll() {
  const api = useApi();
  const { isCpaOwner } = useAuth();
  const [clientId, setClientId] = useState('');
  const [runs, setRuns] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Create run state
  const [showCreate, setShowCreate] = useState(false);
  const [employees, setEmployees] = useState([]);
  const [createForm, setCreateForm] = useState({
    pay_period_start: '',
    pay_period_end: '',
    pay_date: '',
    pay_periods_per_year: '26',
    tax_year: '2026',
    suta_rate: '',
  });
  const [selectedEmployees, setSelectedEmployees] = useState([]);
  const [hoursMap, setHoursMap] = useState({});

  // Detail
  const [detail, setDetail] = useState(null);
  const [confirm, setConfirm] = useState(null);

  const fetchRuns = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/payroll`, { params: { skip: page * 25, limit: 25 } });
      setRuns(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch { /* ignore */ }
    setLoading(false);
  }, [clientId, page, api]);

  useEffect(() => { fetchRuns(); }, [fetchRuns]);

  useEffect(() => {
    if (!clientId) return;
    api.get(`/api/v1/clients/${clientId}/employees`, { params: { active_only: true, limit: 200 } })
      .then((res) => {
        const emps = res.data.items || [];
        setEmployees(emps);
        setSelectedEmployees(emps.map((e) => e.id));
        const hrs = {};
        emps.forEach((e) => { hrs[e.id] = e.pay_type === 'HOURLY' ? '80' : ''; });
        setHoursMap(hrs);
      })
      .catch(() => {});
  }, [clientId, api]);

  const handleCreate = async () => {
    setError('');
    try {
      const employee_items = selectedEmployees.map((empId) => ({
        employee_id: empId,
        hours_worked: hoursMap[empId] ? parseFloat(hoursMap[empId]) : null,
      }));
      const payload = {
        pay_period_start: createForm.pay_period_start,
        pay_period_end: createForm.pay_period_end,
        pay_date: createForm.pay_date,
        pay_periods_per_year: parseInt(createForm.pay_periods_per_year),
        tax_year: parseInt(createForm.tax_year),
        suta_rate: createForm.suta_rate ? parseFloat(createForm.suta_rate) : null,
        employee_items,
      };
      await api.post(`/api/v1/clients/${clientId}/payroll`, payload);
      setShowCreate(false);
      fetchRuns();
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to create payroll run');
    }
  };

  const handleAction = async (action, runId) => {
    try {
      if (action === 'delete') {
        await api.delete(`/api/v1/clients/${clientId}/payroll/${runId}`);
      } else {
        await api.post(`/api/v1/clients/${clientId}/payroll/${runId}/${action}`);
      }
      fetchRuns();
      setDetail(null);
    } catch (e) {
      setError(e.response?.data?.detail || `Failed to ${action}`);
    }
    setConfirm(null);
  };

  const handlePayStub = async (runId, itemId, empName) => {
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/payroll/${runId}/items/${itemId}/pay-stub`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `pay-stub-${empName.replace(/\s+/g, '-')}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate pay stub');
    }
  };

  const fetchDetail = async (run) => {
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/payroll/${run.id}`);
      setDetail(res.data);
    } catch {
      setDetail(run);
    }
  };

  const toggleEmployee = (empId) => {
    setSelectedEmployees((prev) =>
      prev.includes(empId) ? prev.filter((id) => id !== empId) : [...prev, empId]
    );
  };

  const columns = [
    { key: 'pay_period_start', label: 'Period Start', render: (v) => formatDate(v) },
    { key: 'pay_period_end', label: 'Period End', render: (v) => formatDate(v) },
    { key: 'pay_date', label: 'Pay Date', render: (v) => formatDate(v) },
    { key: 'status', label: 'Status', render: (v) => <StatusBadge status={v} /> },
    { key: 'items', label: 'Employees', render: (v) => (v || []).length },
  ];

  const totalGross = detail?.items?.reduce((s, i) => s + parseFloat(i.gross_pay || 0), 0) || 0;
  const totalNet = detail?.items?.reduce((s, i) => s + parseFloat(i.net_pay || 0), 0) || 0;

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Payroll</h1>
        <button className="btn btn--primary" onClick={() => setShowCreate(true)} disabled={!clientId}>New Payroll Run</button>
      </div>

      <ClientSelector value={clientId} onSelect={(id) => { setClientId(id); setPage(0); }} />

      {error && <div className="alert alert--error">{error}</div>}

      <DataTable columns={columns} data={runs} total={total} page={page} onPageChange={setPage} loading={loading} emptyMessage="No payroll runs." onRowClick={fetchDetail} />

      {/* Create Payroll Run */}
      <Modal isOpen={showCreate} onClose={() => setShowCreate(false)} title="New Payroll Run" size="lg">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <FormField label="Period Start">
            <input className="form-input" type="date" value={createForm.pay_period_start} onChange={(e) => setCreateForm({ ...createForm, pay_period_start: e.target.value })} />
          </FormField>
          <FormField label="Period End">
            <input className="form-input" type="date" value={createForm.pay_period_end} onChange={(e) => setCreateForm({ ...createForm, pay_period_end: e.target.value })} />
          </FormField>
          <FormField label="Pay Date">
            <input className="form-input" type="date" value={createForm.pay_date} onChange={(e) => setCreateForm({ ...createForm, pay_date: e.target.value })} />
          </FormField>
        </div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
          <FormField label="Pay Periods/Year">
            <input className="form-input" type="number" value={createForm.pay_periods_per_year} onChange={(e) => setCreateForm({ ...createForm, pay_periods_per_year: e.target.value })} />
          </FormField>
          <FormField label="Tax Year">
            <input className="form-input" type="number" value={createForm.tax_year} onChange={(e) => setCreateForm({ ...createForm, tax_year: e.target.value })} />
          </FormField>
          <FormField label="SUTA Rate (blank=default 2.7%)">
            <input className="form-input" type="number" step="0.001" placeholder="0.027" value={createForm.suta_rate} onChange={(e) => setCreateForm({ ...createForm, suta_rate: e.target.value })} />
          </FormField>
        </div>

        <h4 style={{ marginTop: 16, marginBottom: 8 }}>Employees</h4>
        {employees.length === 0 ? (
          <p className="empty-state">No active employees for this client.</p>
        ) : (
          <table className="table">
            <thead>
              <tr><th style={{ width: 36 }}></th><th>Name</th><th>Type</th><th>Rate</th><th>Hours</th></tr>
            </thead>
            <tbody>
              {employees.map((emp) => (
                <tr key={emp.id}>
                  <td><input type="checkbox" checked={selectedEmployees.includes(emp.id)} onChange={() => toggleEmployee(emp.id)} /></td>
                  <td>{emp.first_name} {emp.last_name}</td>
                  <td>{emp.pay_type}</td>
                  <td>{emp.pay_type === 'SALARY' ? `${formatCurrency(emp.pay_rate)}/yr` : `${formatCurrency(emp.pay_rate)}/hr`}</td>
                  <td>
                    {emp.pay_type === 'HOURLY' ? (
                      <input className="form-input" style={{ width: 80, marginBottom: 0 }} type="number" value={hoursMap[emp.id] || ''} onChange={(e) => setHoursMap({ ...hoursMap, [emp.id]: e.target.value })} />
                    ) : '--'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}

        <div className="form-actions" style={{ marginTop: 16 }}>
          <button className="btn btn--outline" onClick={() => setShowCreate(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleCreate} disabled={selectedEmployees.length === 0}>Create Run</button>
        </div>
      </Modal>

      {/* Payroll Detail */}
      <Modal isOpen={!!detail} onClose={() => setDetail(null)} title={`Payroll Run — ${formatDate(detail?.pay_period_start)} to ${formatDate(detail?.pay_period_end)}`} size="lg">
        {detail && (
          <>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12, marginBottom: 16 }}>
              <div><strong>Pay Date:</strong> {formatDate(detail.pay_date)}</div>
              <div><strong>Status:</strong> <StatusBadge status={detail.status} /></div>
              <div><strong>Employees:</strong> {(detail.items || []).length}</div>
            </div>

            {(detail.items || []).length > 0 && (
              <div className="table-wrapper" style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Employee</th>
                      <th>Gross</th>
                      <th>Fed WH</th>
                      <th>State WH</th>
                      <th>SS</th>
                      <th>Medicare</th>
                      <th>Net</th>
                      <th>Pay Stub</th>
                    </tr>
                  </thead>
                  <tbody>
                    {detail.items.map((item) => {
                      const emp = employees.find((e) => e.id === item.employee_id);
                      const empName = emp ? `${emp.first_name} ${emp.last_name}` : 'Unknown';
                      return (
                        <tr key={item.id}>
                          <td>{empName}</td>
                          <td>{formatCurrency(item.gross_pay)}</td>
                          <td>{formatCurrency(item.federal_withholding)}</td>
                          <td>{formatCurrency(item.state_withholding)}</td>
                          <td>{formatCurrency(item.social_security)}</td>
                          <td>{formatCurrency(item.medicare)}</td>
                          <td><strong>{formatCurrency(item.net_pay)}</strong></td>
                          <td>
                            <button className="btn btn--small btn--outline" onClick={() => handlePayStub(detail.id, item.id, empName)}>PDF</button>
                          </td>
                        </tr>
                      );
                    })}
                    <tr style={{ fontWeight: 700 }}>
                      <td>Total</td>
                      <td>{formatCurrency(totalGross)}</td>
                      <td colSpan={4}></td>
                      <td>{formatCurrency(totalNet)}</td>
                      <td></td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}

            <div className="form-actions" style={{ marginTop: 16 }}>
              {detail.status === 'DRAFT' && (
                <button className="btn btn--primary" onClick={() => handleAction('submit', detail.id)}>Submit for Approval</button>
              )}
              <RoleGate role="CPA_OWNER">
                {detail.status === 'PENDING_APPROVAL' && (
                  <button className="btn btn--primary" onClick={() => setConfirm({ action: 'finalize', id: detail.id, msg: 'Finalize this payroll run? This will post to the general ledger.' })}>Finalize</button>
                )}
                {['DRAFT', 'PENDING_APPROVAL'].includes(detail.status) && (
                  <button className="btn btn--danger" onClick={() => setConfirm({ action: 'void', id: detail.id, msg: 'Void this payroll run?' })}>Void</button>
                )}
              </RoleGate>
            </div>
          </>
        )}
      </Modal>

      <ConfirmDialog
        isOpen={!!confirm}
        title="Confirm"
        message={confirm?.msg}
        confirmLabel="Confirm"
        confirmVariant={confirm?.action === 'void' ? 'danger' : 'primary'}
        onConfirm={() => handleAction(confirm.action, confirm.id)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
