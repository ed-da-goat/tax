import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatCurrency } from '../utils/format';

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export default function Budgets() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showReport, setShowReport] = useState(null);
  const [selectedClient, setSelectedClient] = useState('');
  const [yearFilter, setYearFilter] = useState('');

  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const clientList = clients?.items || [];

  const { data } = useApiQuery(
    ['budgets', selectedClient, yearFilter],
    `/api/v1/clients/${selectedClient}/budgets${yearFilter ? `?fiscal_year=${yearFilter}` : ''}`,
    { enabled: !!selectedClient }
  );

  const { data: accounts } = useApiQuery(
    ['coa', selectedClient],
    `/api/v1/clients/${selectedClient}/accounts`,
    { enabled: !!selectedClient }
  );

  const createBudget = useApiMutation('post', `/api/v1/clients/${selectedClient}/budgets`, { invalidate: [['budgets']] });
  const deleteBudget = useApiMutation('delete', (body) => `/api/v1/clients/${selectedClient}/budgets/${body.id}`, { invalidate: [['budgets']] });

  const [form, setForm] = useState({ name: '', fiscal_year: new Date().getFullYear(), description: '', lines: [] });

  function addBudgetLine() {
    setForm(f => ({
      ...f,
      lines: [...f.lines, {
        account_id: '', month_1: 0, month_2: 0, month_3: 0, month_4: 0,
        month_5: 0, month_6: 0, month_7: 0, month_8: 0, month_9: 0,
        month_10: 0, month_11: 0, month_12: 0,
      }],
    }));
  }

  function updateBudgetLine(i, field, val) {
    setForm(f => ({
      ...f,
      lines: f.lines.map((l, j) => j === i ? { ...l, [field]: val } : l),
    }));
  }

  async function handleCreate(e) {
    e.preventDefault();
    try {
      const payload = {
        ...form,
        fiscal_year: parseInt(form.fiscal_year),
        lines: form.lines.map(l => ({
          ...l,
          month_1: parseFloat(l.month_1) || 0, month_2: parseFloat(l.month_2) || 0,
          month_3: parseFloat(l.month_3) || 0, month_4: parseFloat(l.month_4) || 0,
          month_5: parseFloat(l.month_5) || 0, month_6: parseFloat(l.month_6) || 0,
          month_7: parseFloat(l.month_7) || 0, month_8: parseFloat(l.month_8) || 0,
          month_9: parseFloat(l.month_9) || 0, month_10: parseFloat(l.month_10) || 0,
          month_11: parseFloat(l.month_11) || 0, month_12: parseFloat(l.month_12) || 0,
        })),
      };
      await createBudget.mutateAsync(payload);
      setShowAdd(false);
      setForm({ name: '', fiscal_year: new Date().getFullYear(), description: '', lines: [] });
      setToast({ type: 'success', message: 'Budget created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // Budget vs Actual report
  const { data: reportData } = useApiQuery(
    ['budget-vs-actual', showReport],
    `/api/v1/clients/${selectedClient}/budgets/${showReport}/vs-actual`,
    { enabled: !!showReport }
  );

  const items = data?.items || [];
  const acctList = accounts?.items || [];

  const columns = [
    { key: 'name', label: 'Budget Name' },
    { key: 'fiscal_year', label: 'Year' },
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    { key: 'lines', label: 'Accounts', render: (row) => row.lines?.length || 0 },
    { key: 'is_active', label: 'Active', render: (row) => row.is_active ? 'Yes' : 'No' },
    { key: 'actions', label: '', render: (row) => (
      <div style={{ display: 'flex', gap: '4px' }}>
        <button className="btn btn--small btn--primary" onClick={() => setShowReport(row.id)}>vs Actual</button>
        <button className="btn btn--small btn--danger" onClick={() => deleteBudget.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Deleted' }))}>Delete</button>
      </div>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Budgets</h1>
        {selectedClient && <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ New Budget</button>}
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <select value={selectedClient} onChange={e => setSelectedClient(e.target.value)}>
          <option value="">Select Client...</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <input type="number" placeholder="Year" value={yearFilter} onChange={e => setYearFilter(e.target.value)} style={{ width: '100px' }} />
      </div>

      {selectedClient ? (
        <DataTable columns={columns} rows={items} emptyMessage="No budgets found" />
      ) : (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>Select a client to view budgets</div>
      )}

      {/* Create Budget Modal */}
      {showAdd && (
        <Modal title="New Budget" onClose={() => setShowAdd(false)} wide>
          <form onSubmit={handleCreate}>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: '12px' }}>
              <FormField label="Budget Name" required>
                <input value={form.name} onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required />
              </FormField>
              <FormField label="Fiscal Year" required>
                <input type="number" value={form.fiscal_year} onChange={e => setForm(f => ({ ...f, fiscal_year: e.target.value }))} required />
              </FormField>
            </div>
            <FormField label="Description">
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} />
            </FormField>

            <h3 style={{ marginTop: '16px' }}>Budget Lines ({form.lines.length})</h3>
            <div style={{ overflowX: 'auto' }}>
              {form.lines.map((line, i) => (
                <div key={i} style={{ display: 'flex', gap: '4px', marginBottom: '6px', alignItems: 'center' }}>
                  <select value={line.account_id} onChange={e => updateBudgetLine(i, 'account_id', e.target.value)} style={{ minWidth: '180px' }} required>
                    <option value="">Account...</option>
                    {acctList.map(a => <option key={a.id} value={a.id}>{a.account_number} — {a.name}</option>)}
                  </select>
                  {MONTHS.map((m, mi) => (
                    <input key={m} type="number" step="0.01" placeholder={m} title={m}
                      value={line[`month_${mi + 1}`]} onChange={e => updateBudgetLine(i, `month_${mi + 1}`, e.target.value)}
                      style={{ width: '70px' }} />
                  ))}
                  <button type="button" className="btn btn--small btn--danger" onClick={() => setForm(f => ({ ...f, lines: f.lines.filter((_, j) => j !== i) }))}>X</button>
                </div>
              ))}
            </div>
            <button type="button" className="btn btn--small btn--outline" onClick={addBudgetLine}>+ Add Account Line</button>

            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createBudget.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Budget vs Actual Report Modal */}
      {showReport && reportData && (
        <Modal title={`Budget vs Actual — ${reportData.budget_name} (${reportData.fiscal_year})`} onClose={() => setShowReport(null)} wide>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Account</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Budget</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Actual</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Variance</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>%</th>
              </tr>
            </thead>
            <tbody>
              {(reportData.lines || []).map((line, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '8px' }}>{line.account_number} — {line.account_name}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(line.budget_amount)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(line.actual_amount)}</td>
                  <td style={{ padding: '8px', textAlign: 'right', color: parseFloat(line.variance) < 0 ? '#EF4444' : '#10B981' }}>
                    {formatCurrency(line.variance)}
                  </td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>
                    {line.variance_pct != null ? `${parseFloat(line.variance_pct).toFixed(1)}%` : '—'}
                  </td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr style={{ borderTop: '2px solid #374151', fontWeight: 600 }}>
                <td style={{ padding: '8px' }}>Total</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(reportData.total_budget)}</td>
                <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(reportData.total_actual)}</td>
                <td style={{ padding: '8px', textAlign: 'right', color: parseFloat(reportData.total_variance) < 0 ? '#EF4444' : '#10B981' }}>
                  {formatCurrency(reportData.total_variance)}
                </td>
                <td />
              </tr>
            </tfoot>
          </table>
          <div className="modal-actions">
            <button type="button" className="btn btn--outline" onClick={() => setShowReport(null)}>Close</button>
          </div>
        </Modal>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
