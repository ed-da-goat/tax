import { useState } from 'react';
import useApi from '../hooks/useApi';
import ClientSelector from '../components/ClientSelector';
import RoleGate from '../components/RoleGate';
import Tabs from '../components/Tabs';
import { formatCurrency, formatDate } from '../utils/format';

const FORM_TABS = [
  { key: 'g7', label: 'GA G-7' },
  { key: '500', label: 'GA 500' },
  { key: '600', label: 'GA 600' },
  { key: 'st3', label: 'GA ST-3' },
  { key: 'schedule-c', label: 'Schedule C' },
  { key: '1120s', label: '1120-S' },
  { key: '1120', label: '1120' },
  { key: '1065', label: '1065' },
  { key: 'checklist', label: 'Checklist' },
  { key: 'w2', label: 'W-2' },
  { key: '1099', label: '1099-NEC' },
];

const API_MAP = {
  g7: 'g7',
  500: 'form-500',
  600: 'form-600',
  st3: 'st3',
  'schedule-c': 'schedule-c',
  '1120s': 'form-1120s',
  1120: 'form-1120',
  1065: 'form-1065',
  checklist: 'checklist',
  w2: 'w2',
  1099: '1099-nec',
};

export default function TaxExports() {
  const api = useApi();
  const [clientId, setClientId] = useState('');
  const [tab, setTab] = useState('g7');
  const [taxYear, setTaxYear] = useState(2026);
  const [quarter, setQuarter] = useState(1);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [data, setData] = useState(null);

  const fetchForm = async () => {
    if (!clientId) return;
    setLoading(true); setError(''); setData(null);
    try {
      const params = { tax_year: taxYear };
      if (tab === 'g7') params.quarter = quarter;
      if (tab === 'st3') {
        params.period_start = `${taxYear}-01-01`;
        params.period_end = `${taxYear}-12-31`;
      }
      const endpoint = API_MAP[tab];
      const res = await api.get(`/api/v1/tax/clients/${clientId}/${endpoint}`, { params });
      setData(res.data);
    } catch (e) {
      setError(e.response?.data?.detail || 'Failed to generate form data');
    }
    setLoading(false);
  };

  const renderG7 = () => data && (
    <div className="card">
      <h3>Georgia Form G-7 — Q{data.quarter} {data.tax_year}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
        Due: {formatDate(data.due_date)} | Client: {data.client_name}
      </p>
      <table className="table">
        <thead><tr><th>Month</th><th>GA Withholding</th><th>Employees</th></tr></thead>
        <tbody>
          {(data.monthly_details || []).map((m) => (
            <tr key={m.month}><td>{m.month_name}</td><td>{formatCurrency(m.georgia_withholding)}</td><td>{m.employee_count}</td></tr>
          ))}
          <tr style={{ fontWeight: 700 }}>
            <td>Total</td><td>{formatCurrency(data.total_withholding)}</td><td>{data.total_employees}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );

  const renderIncomeForm = (title) => data && (
    <div className="card">
      <h3>{title} — TY{data.tax_year}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>Client: {data.client_name} ({data.entity_type?.replace(/_/g, ' ')})</p>
      <table className="table">
        <tbody>
          <tr><td>Gross Revenue / Receipts</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.gross_receipts ?? data.gross_revenue)}</td></tr>
          {data.cost_of_goods_sold != null && <tr><td>Cost of Goods Sold</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.cost_of_goods_sold)}</td></tr>}
          {data.gross_profit != null && <tr><td>Gross Profit</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.gross_profit)}</td></tr>}
          <tr><td>Total Expenses / Deductions</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.total_expenses ?? data.total_deductions)}</td></tr>
          <tr style={{ fontWeight: 700 }}><td>Net / Taxable Income</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.net_income ?? data.net_profit ?? data.taxable_income ?? data.ordinary_business_income)}</td></tr>
        </tbody>
      </table>
      {data.expense_categories && Object.keys(data.expense_categories).length > 0 && (
        <>
          <h4 style={{ marginTop: 16, marginBottom: 8 }}>Expense Breakdown</h4>
          <table className="table">
            <thead><tr><th>Category</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
            <tbody>
              {Object.entries(data.expense_categories).map(([cat, amt]) => (
                <tr key={cat}><td>{cat}</td><td style={{ textAlign: 'right' }}>{formatCurrency(amt)}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      {data.total_assets != null && (
        <>
          <h4 style={{ marginTop: 16, marginBottom: 8 }}>Balance Sheet Summary</h4>
          <table className="table">
            <tbody>
              <tr><td>Total Assets</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.total_assets)}</td></tr>
              <tr><td>Total Liabilities</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.total_liabilities)}</td></tr>
              <tr><td>Equity</td><td style={{ textAlign: 'right' }}>{formatCurrency(data.total_equity ?? data.shareholders_equity ?? data.partners_equity ?? data.retained_earnings)}</td></tr>
            </tbody>
          </table>
        </>
      )}
    </div>
  );

  const renderST3 = () => data && (
    <div className="card">
      <h3>Georgia Form ST-3 — TY{data.tax_year}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>Client: {data.client_name} | Period: {formatDate(data.period_start)} — {formatDate(data.period_end)}</p>
      <table className="table">
        <thead><tr><th>Jurisdiction</th><th>Gross Sales</th><th>Exempt</th><th>Taxable</th><th>Tax Collected</th></tr></thead>
        <tbody>
          {(data.line_items || []).map((li, i) => (
            <tr key={i}><td>{li.jurisdiction}</td><td>{formatCurrency(li.gross_sales)}</td><td>{formatCurrency(li.exempt_sales)}</td><td>{formatCurrency(li.taxable_sales)}</td><td>{formatCurrency(li.tax_collected)}</td></tr>
          ))}
          <tr style={{ fontWeight: 700 }}>
            <td>Total</td><td>{formatCurrency(data.total_gross_sales)}</td><td>{formatCurrency(data.total_exempt_sales)}</td><td>{formatCurrency(data.total_taxable_sales)}</td><td>{formatCurrency(data.total_tax_collected)}</td>
          </tr>
        </tbody>
      </table>
    </div>
  );

  const renderChecklist = () => data && (
    <div className="card">
      <h3>Tax Document Checklist — TY{data.tax_year}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>Client: {data.client_name} ({data.entity_type?.replace(/_/g, ' ')}) | {data.total_received}/{data.total_required} received</p>
      <table className="table">
        <thead><tr><th>Document</th><th>Required</th><th>Status</th><th>Notes</th></tr></thead>
        <tbody>
          {(data.items || []).map((item, i) => (
            <tr key={i}>
              <td>{item.document}</td>
              <td>{item.required ? 'Yes' : 'No'}</td>
              <td><span className={`badge ${item.status === 'RECEIVED' ? 'badge--paid' : item.status === 'NOT_APPLICABLE' ? 'badge--draft' : 'badge--pending'}`}>{item.status}</span></td>
              <td>{item.notes || '--'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );

  const downloadPdf = async (url, filename) => {
    try {
      const res = await api.get(url, { params: { tax_year: taxYear }, responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (e) {
      setError(e.response?.data?.detail || 'PDF download failed');
    }
  };

  const renderW2 = () => data && (
    <div className="card">
      <h3>W-2 Forms — TY{data.tax_year || taxYear}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
        Employer: {data.employer_name} | {data.employer_address}
      </p>
      <div style={{ marginBottom: 16 }}>
        <button className="btn btn--outline" onClick={() => downloadPdf(`/api/v1/tax/clients/${clientId}/w2/pdf`, `w2-all-${clientId}-${taxYear}.pdf`)}>
          Download All W-2s (PDF)
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Employee</th>
            <th>SSN</th>
            <th style={{ textAlign: 'right' }}>Box 1 Wages</th>
            <th style={{ textAlign: 'right' }}>Box 2 Fed W/H</th>
            <th style={{ textAlign: 'right' }}>Box 3 SS Wages</th>
            <th style={{ textAlign: 'right' }}>Box 4 SS W/H</th>
            <th style={{ textAlign: 'right' }}>Box 5 Med Wages</th>
            <th style={{ textAlign: 'right' }}>Box 6 Med W/H</th>
            <th style={{ textAlign: 'right' }}>Box 16 State Wages</th>
            <th style={{ textAlign: 'right' }}>Box 17 State W/H</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {(data.w2s || []).map((w) => (
            <tr key={w.employee_id}>
              <td>{w.employee_name}</td>
              <td>{w.ssn_masked}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box1_wages)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box2_fed_withheld)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box3_ss_wages)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box4_ss_withheld)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box5_medicare_wages)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box6_medicare_withheld)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box16_state_wages)}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(w.box17_state_withheld)}</td>
              <td>
                <button className="btn btn--small btn--outline" onClick={() => downloadPdf(`/api/v1/tax/clients/${clientId}/w2/${w.employee_id}/pdf`, `w2-${w.employee_id}-${taxYear}.pdf`)}>
                  PDF
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(data.w2s || []).length === 0 && (
        <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>No W-2 data found for this client and tax year.</p>
      )}
    </div>
  );

  const renderForm1099 = () => data && (
    <div className="card">
      <h3>1099-NEC Forms — TY{data.tax_year || taxYear}</h3>
      <p style={{ color: 'var(--color-text-muted)', marginBottom: 16 }}>
        Payer: {data.payer_name} | {data.payer_address}
      </p>
      <div style={{ marginBottom: 16 }}>
        <button className="btn btn--outline" onClick={() => downloadPdf(`/api/v1/tax/clients/${clientId}/1099-nec/pdf`, `1099-nec-all-${clientId}-${taxYear}.pdf`)}>
          Download All 1099-NECs (PDF)
        </button>
      </div>
      <table className="table">
        <thead>
          <tr>
            <th>Vendor</th>
            <th>TIN</th>
            <th style={{ textAlign: 'right' }}>Nonemployee Compensation</th>
            <th>Payer TIN</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {(data.forms || []).map((f) => (
            <tr key={f.vendor_id}>
              <td>{f.vendor_name}</td>
              <td>{f.vendor_tin_masked}</td>
              <td style={{ textAlign: 'right' }}>{formatCurrency(f.nonemployee_compensation)}</td>
              <td>{f.payer_tin_masked}</td>
              <td>
                <button className="btn btn--small btn--outline" onClick={() => downloadPdf(`/api/v1/tax/clients/${clientId}/1099-nec/${f.vendor_id}/pdf`, `1099-nec-${f.vendor_id}-${taxYear}.pdf`)}>
                  PDF
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      {(data.forms || []).length === 0 && (
        <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>No 1099-NEC data found for this client and tax year.</p>
      )}
    </div>
  );

  const formTitles = {
    500: 'Georgia Form 500 (Individual)',
    600: 'Georgia Form 600 (Corporate)',
    'schedule-c': 'Federal Schedule C',
    '1120s': 'Federal Form 1120-S',
    1120: 'Federal Form 1120',
    1065: 'Federal Form 1065',
  };

  return (
    <RoleGate role="CPA_OWNER" fallback={<div className="page"><h1 className="page-title">Tax Exports</h1><p className="empty-state">CPA Owner access required.</p></div>}>
      <div className="page" style={{ maxWidth: 1200 }}>
        <div className="page-header">
          <h1 className="page-title">Tax Form Exports</h1>
        </div>

        <Tabs tabs={FORM_TABS} activeTab={tab} onTabChange={(t) => { setTab(t); setData(null); }} />

        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginTop: 16, marginBottom: 16 }}>
          <ClientSelector value={clientId} onSelect={setClientId} />
          <div>
            <label className="form-label">Tax Year</label>
            <input className="form-input" type="number" style={{ width: 100, marginBottom: 0 }} value={taxYear} onChange={(e) => setTaxYear(parseInt(e.target.value))} />
          </div>
          {tab === 'g7' && (
            <div>
              <label className="form-label">Quarter</label>
              <select className="form-input form-select" style={{ width: 80, marginBottom: 0 }} value={quarter} onChange={(e) => setQuarter(parseInt(e.target.value))}>
                <option value={1}>Q1</option><option value={2}>Q2</option><option value={3}>Q3</option><option value={4}>Q4</option>
              </select>
            </div>
          )}
          <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 0 }} onClick={fetchForm} disabled={!clientId || loading}>
            Generate
          </button>
        </div>

        {error && <div className="alert alert--error">{error}</div>}

        {loading && <div className="spinner" />}
        {!loading && !data && !error && (
          <div className="empty-state">
            <div className="empty-state-heading">Select a client and tax year</div>
            <div className="empty-state-text">Click Generate to view form data for the selected tab.</div>
          </div>
        )}
        {tab === 'g7' && renderG7()}
        {tab === 'st3' && renderST3()}
        {tab === 'checklist' && renderChecklist()}
        {['500', '600', 'schedule-c', '1120s', '1120', '1065'].includes(tab) && renderIncomeForm(formTitles[tab])}
        {tab === 'w2' && renderW2()}
        {tab === '1099' && renderForm1099()}
      </div>
    </RoleGate>
  );
}
