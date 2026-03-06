import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';
import { formatCurrency, formatDate } from '../utils/format';

const STATUS_COLORS = {
  ACTIVE: '#10B981', FULLY_DEPRECIATED: '#3d6d8e', DISPOSED: '#EF4444', TRANSFERRED: '#9CA3AF',
};

const DEPRECIATION_METHODS = [
  { value: 'STRAIGHT_LINE', label: 'Straight Line' },
  { value: 'MACRS_GDS', label: 'MACRS GDS' },
  { value: 'MACRS_ADS', label: 'MACRS ADS' },
  { value: 'SECTION_179', label: 'Section 179' },
  { value: 'BONUS', label: 'Bonus Depreciation' },
  { value: 'NONE', label: 'None' },
];

const MACRS_CLASSES = ['3', '5', '7', '10', '15', '20', '27.5', '39'];

export default function FixedAssets() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [showDispose, setShowDispose] = useState(null);
  const [showSchedule, setShowSchedule] = useState(null);
  const [selectedClient, setSelectedClient] = useState('');
  const [statusFilter, setStatusFilter] = useState('');

  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const clientList = clients?.items || [];

  const params = new URLSearchParams();
  if (statusFilter) params.set('status', statusFilter);

  const { data } = useApiQuery(
    ['fixed-assets', selectedClient, statusFilter],
    `/api/v1/clients/${selectedClient}/fixed-assets?${params}`,
    { enabled: !!selectedClient }
  );

  const createAsset = useApiMutation('post', `/api/v1/clients/${selectedClient}/fixed-assets`, { invalidate: [['fixed-assets']] });
  const disposeAsset = useApiMutation('post', (body) => `/api/v1/clients/${selectedClient}/fixed-assets/${body.asset_id}/dispose`, { invalidate: [['fixed-assets']] });

  const [form, setForm] = useState({
    asset_name: '', asset_number: '', description: '', category: '',
    acquisition_date: '', acquisition_cost: '', depreciation_method: 'MACRS_GDS',
    useful_life_years: '', salvage_value: '0', macrs_class: '7',
    location: '', serial_number: '',
  });

  const [disposeForm, setDisposeForm] = useState({ disposal_date: '', disposal_amount: '0', disposal_method: 'SOLD' });

  async function handleCreate(e) {
    e.preventDefault();
    try {
      await createAsset.mutateAsync({
        ...form,
        acquisition_cost: parseFloat(form.acquisition_cost),
        salvage_value: parseFloat(form.salvage_value || '0'),
        useful_life_years: form.useful_life_years ? parseInt(form.useful_life_years) : null,
        asset_number: form.asset_number || null,
        description: form.description || null,
        category: form.category || null,
        location: form.location || null,
        serial_number: form.serial_number || null,
      });
      setShowAdd(false);
      setToast({ type: 'success', message: 'Asset created with depreciation schedule' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  async function handleDispose(e) {
    e.preventDefault();
    try {
      await disposeAsset.mutateAsync({
        asset_id: showDispose,
        disposal_date: disposeForm.disposal_date,
        disposal_amount: parseFloat(disposeForm.disposal_amount),
        disposal_method: disposeForm.disposal_method,
      });
      setShowDispose(null);
      setToast({ type: 'success', message: 'Asset disposed' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  const items = data?.items || [];

  const columns = [
    { key: 'asset_name', label: 'Asset' },
    { key: 'asset_number', label: '#', render: (row) => row.asset_number || '—' },
    { key: 'category', label: 'Category', render: (row) => row.category || '—' },
    { key: 'acquisition_date', label: 'Acquired', render: (row) => formatDate(row.acquisition_date) },
    { key: 'acquisition_cost', label: 'Cost', render: (row) => formatCurrency(row.acquisition_cost) },
    { key: 'depreciation_method', label: 'Method', render: (row) => row.depreciation_method.replace('_', ' ') },
    { key: 'accumulated_depreciation', label: 'Accum. Depr.', render: (row) => formatCurrency(row.accumulated_depreciation) },
    { key: 'book_value', label: 'Book Value', render: (row) => formatCurrency(row.book_value) },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: STATUS_COLORS[row.status] }}>{row.status.replace('_', ' ')}</span>
    )},
    { key: 'actions', label: '', render: (row) => (
      <div style={{ display: 'flex', gap: '4px' }}>
        {row.depreciation_schedule?.length > 0 && (
          <button className="btn btn--small btn--outline" onClick={() => setShowSchedule(row)}>Schedule</button>
        )}
        {row.status === 'ACTIVE' && (
          <button className="btn btn--small btn--danger" onClick={() => setShowDispose(row.id)}>Dispose</button>
        )}
      </div>
    )},
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Fixed Assets</h1>
        {selectedClient && <button className="btn btn--primary" onClick={() => setShowAdd(true)}>+ Add Asset</button>}
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <select value={selectedClient} onChange={e => setSelectedClient(e.target.value)}>
          <option value="">Select Client...</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
        <select value={statusFilter} onChange={e => setStatusFilter(e.target.value)}>
          <option value="">All Statuses</option>
          {Object.keys(STATUS_COLORS).map(s => <option key={s} value={s}>{s.replace('_', ' ')}</option>)}
        </select>
      </div>

      {selectedClient ? (
        <DataTable columns={columns} rows={items} emptyMessage="No fixed assets" />
      ) : (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>Select a client to view fixed assets</div>
      )}

      {/* Add Asset Modal */}
      <Modal isOpen={showAdd} title="Add Fixed Asset" onClose={() => setShowAdd(false)} size="lg">
          <form onSubmit={handleCreate}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <FormField label="Asset Name" required>
                <input value={form.asset_name} onChange={e => setForm(f => ({ ...f, asset_name: e.target.value }))} required />
              </FormField>
              <FormField label="Asset Number">
                <input value={form.asset_number} onChange={e => setForm(f => ({ ...f, asset_number: e.target.value }))} />
              </FormField>
              <FormField label="Category">
                <select value={form.category} onChange={e => setForm(f => ({ ...f, category: e.target.value }))}>
                  <option value="">Select...</option>
                  <option value="Equipment">Equipment</option>
                  <option value="Furniture">Furniture</option>
                  <option value="Vehicles">Vehicles</option>
                  <option value="Buildings">Buildings</option>
                  <option value="Land Improvements">Land Improvements</option>
                  <option value="Computer Equipment">Computer Equipment</option>
                  <option value="Software">Software</option>
                </select>
              </FormField>
              <FormField label="Serial Number">
                <input value={form.serial_number} onChange={e => setForm(f => ({ ...f, serial_number: e.target.value }))} />
              </FormField>
              <FormField label="Acquisition Date" required>
                <input type="date" value={form.acquisition_date} onChange={e => setForm(f => ({ ...f, acquisition_date: e.target.value }))} required />
              </FormField>
              <FormField label="Acquisition Cost" required>
                <input type="number" step="0.01" min="0.01" value={form.acquisition_cost} onChange={e => setForm(f => ({ ...f, acquisition_cost: e.target.value }))} required />
              </FormField>
            </div>
            <h3 style={{ marginTop: '16px' }}>Depreciation</h3>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '12px' }}>
              <FormField label="Method">
                <select value={form.depreciation_method} onChange={e => setForm(f => ({ ...f, depreciation_method: e.target.value }))}>
                  {DEPRECIATION_METHODS.map(m => <option key={m.value} value={m.value}>{m.label}</option>)}
                </select>
              </FormField>
              {(form.depreciation_method === 'MACRS_GDS' || form.depreciation_method === 'MACRS_ADS') && (
                <FormField label="MACRS Class (years)">
                  <select value={form.macrs_class} onChange={e => setForm(f => ({ ...f, macrs_class: e.target.value }))}>
                    {MACRS_CLASSES.map(c => <option key={c} value={c}>{c}-year</option>)}
                  </select>
                </FormField>
              )}
              {form.depreciation_method === 'STRAIGHT_LINE' && (
                <FormField label="Useful Life (years)">
                  <input type="number" min="1" value={form.useful_life_years} onChange={e => setForm(f => ({ ...f, useful_life_years: e.target.value }))} />
                </FormField>
              )}
              <FormField label="Salvage Value">
                <input type="number" step="0.01" min="0" value={form.salvage_value} onChange={e => setForm(f => ({ ...f, salvage_value: e.target.value }))} />
              </FormField>
            </div>
            <FormField label="Location">
              <input value={form.location} onChange={e => setForm(f => ({ ...f, location: e.target.value }))} />
            </FormField>
            <FormField label="Description">
              <textarea value={form.description} onChange={e => setForm(f => ({ ...f, description: e.target.value }))} rows={2} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAdd(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createAsset.isPending}>Create</button>
            </div>
          </form>
      </Modal>

      {/* Dispose Modal */}
      <Modal isOpen={!!showDispose} title="Dispose Asset" onClose={() => setShowDispose(null)}>
          <form onSubmit={handleDispose}>
            <FormField label="Disposal Date" required>
              <input type="date" value={disposeForm.disposal_date} onChange={e => setDisposeForm(f => ({ ...f, disposal_date: e.target.value }))} required />
            </FormField>
            <FormField label="Disposal Amount">
              <input type="number" step="0.01" min="0" value={disposeForm.disposal_amount} onChange={e => setDisposeForm(f => ({ ...f, disposal_amount: e.target.value }))} />
            </FormField>
            <FormField label="Disposal Method">
              <select value={disposeForm.disposal_method} onChange={e => setDisposeForm(f => ({ ...f, disposal_method: e.target.value }))}>
                <option value="SOLD">Sold</option>
                <option value="SCRAPPED">Scrapped</option>
                <option value="DONATED">Donated</option>
                <option value="TRADED_IN">Traded In</option>
              </select>
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowDispose(null)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={disposeAsset.isPending}>Dispose</button>
            </div>
          </form>
      </Modal>

      {/* Depreciation Schedule Modal */}
      <Modal isOpen={!!showSchedule} title={`Depreciation Schedule — ${showSchedule?.asset_name}`} onClose={() => setShowSchedule(null)} size="lg">
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                <th style={{ padding: '8px', textAlign: 'left' }}>Year</th>
                <th style={{ padding: '8px', textAlign: 'left' }}>Period</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Depreciation</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Accumulated</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>Book Value</th>
              </tr>
            </thead>
            <tbody>
              {(showSchedule?.depreciation_schedule || []).map((entry, i) => (
                <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                  <td style={{ padding: '8px' }}>{entry.fiscal_year}</td>
                  <td style={{ padding: '8px' }}>{formatDate(entry.period_start)} — {formatDate(entry.period_end)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(entry.depreciation_amount)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(entry.accumulated_total)}</td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>{formatCurrency(entry.book_value_end)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="modal-actions">
            <button type="button" className="btn btn--outline" onClick={() => setShowSchedule(null)}>Close</button>
          </div>
      </Modal>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
