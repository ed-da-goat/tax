import { useState } from 'react';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import ClientSelector from '../components/ClientSelector';
import Tabs from '../components/Tabs';
import RoleGate from '../components/RoleGate';
import { formatCurrency, formatDate } from '../utils/format';

const TABS = [
  { key: 'pl', label: 'Profit & Loss' },
  { key: 'bs', label: 'Balance Sheet' },
  { key: 'cf', label: 'Cash Flow' },
  { key: 'dashboard', label: 'Firm Dashboard' },
  { key: 'ar-aging', label: 'AR Aging' },
  { key: 'ap-aging', label: 'AP Aging' },
];

export default function Reports() {
  const api = useApi();
  const { isCpaOwner } = useAuth();
  const [clientId, setClientId] = useState('');
  const [tab, setTab] = useState('pl');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // P&L / Cash Flow date range
  const [startDate, setStartDate] = useState(() => {
    const d = new Date(); d.setMonth(0, 1);
    return d.toISOString().slice(0, 10);
  });
  const [endDate, setEndDate] = useState(new Date().toISOString().slice(0, 10));

  // Balance sheet as-of
  const [asOfDate, setAsOfDate] = useState(new Date().toISOString().slice(0, 10));

  // Report data
  const [plData, setPlData] = useState(null);
  const [bsData, setBsData] = useState(null);
  const [cfData, setCfData] = useState(null);
  const [dashData, setDashData] = useState(null);
  const [arData, setArData] = useState(null);
  const [apData, setApData] = useState(null);

  const fetchPL = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/profit-loss`, {
        params: { period_start: startDate, period_end: endDate },
      });
      setPlData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const fetchBS = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/balance-sheet`, {
        params: { as_of_date: asOfDate },
      });
      setBsData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const fetchCF = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/cash-flow`, {
        params: { period_start: startDate, period_end: endDate },
      });
      setCfData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const fetchDashboard = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.get('/api/v1/reports/dashboard', {
        params: { period_start: startDate, period_end: endDate },
      });
      setDashData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load dashboard'); }
    setLoading(false);
  };

  const fetchARaging = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/ar-aging`, {
        params: { as_of_date: asOfDate },
      });
      setArData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const fetchAPaging = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/ap-aging`, {
        params: { as_of_date: asOfDate },
      });
      setApData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const downloadFile = async (url, params, filename, mimeType) => {
    try {
      const res = await api.get(url, { params, responseType: 'blob' });
      const blobUrl = window.URL.createObjectURL(new Blob([res.data], { type: mimeType }));
      const link = document.createElement('a');
      link.href = blobUrl;
      link.setAttribute('download', filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(blobUrl);
    } catch (e) {
      setError(e.response?.data?.detail || 'Export failed');
    }
  };

  const getReportParams = (type) => (type === 'balance-sheet' || type === 'ar-aging' || type === 'ap-aging')
    ? { as_of_date: asOfDate }
    : { period_start: startDate, period_end: endDate };

  const exportPdf = (type) => clientId && downloadFile(
    `/api/v1/reports/clients/${clientId}/${type}/pdf`,
    getReportParams(type), `${type}-${clientId}.pdf`, 'application/pdf'
  );
  const exportCsv = (type) => clientId && downloadFile(
    `/api/v1/reports/clients/${clientId}/${type}/csv`,
    getReportParams(type), `${type}-${clientId}.csv`, 'text/csv'
  );
  const exportXlsx = (type) => clientId && downloadFile(
    `/api/v1/reports/clients/${clientId}/${type}/xlsx`,
    getReportParams(type), `${type}-${clientId}.xlsx`,
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
  );

  const ExportButtons = ({ type, data }) => (
    data ? (
      <RoleGate role="CPA_OWNER">
        <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportPdf(type)}>PDF</button>
        <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportCsv(type)}>CSV</button>
        <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportXlsx(type)}>Excel</button>
      </RoleGate>
    ) : null
  );

  const renderAccountRows = (rows) => (
    rows.map((r, i) => (
      <tr key={i}>
        <td style={{ paddingLeft: 24 }}>{r.account_number}</td>
        <td>{r.account_name}</td>
        <td style={{ textAlign: 'right' }}>{formatCurrency(r.balance)}</td>
      </tr>
    ))
  );

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      <div className="page-header">
        <h1 className="page-title">Reports</h1>
      </div>

      <Tabs tabs={TABS} activeTab={tab} onTabChange={setTab} />

      {error && <div className="alert alert--error" style={{ marginTop: 16 }}>{error}</div>}

      <div style={{ marginTop: 16 }}>
        {/* Profit & Loss */}
        {tab === 'pl' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <ClientSelector value={clientId} onSelect={setClientId} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchPL} disabled={!clientId || loading}>Generate</button>
              <ExportButtons type="profit-loss" data={plData} />
            </div>
            {loading && !plData && <div className="spinner" />}
            {!loading && !plData && (
              <div className="empty-state">
                <div className="empty-state-heading">Select a client and date range</div>
                <div className="empty-state-text">Click Generate to view the Profit &amp; Loss report.</div>
              </div>
            )}
            {plData && (
              <div className="card">
                <h3 style={{ marginBottom: 16 }}>Profit & Loss — {formatDate(plData.period_start)} to {formatDate(plData.period_end)}</h3>
                <table className="table">
                  <thead><tr><th>Account #</th><th>Account</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                  <tbody>
                    <tr style={{ fontWeight: 700 }}><td colSpan={2}>Revenue</td><td style={{ textAlign: 'right' }}>{formatCurrency(plData.total_revenue)}</td></tr>
                    {renderAccountRows(plData.revenue_items || [])}
                    <tr style={{ fontWeight: 700 }}><td colSpan={2}>Expenses</td><td style={{ textAlign: 'right' }}>{formatCurrency(plData.total_expenses)}</td></tr>
                    {renderAccountRows(plData.expense_items || [])}
                    <tr style={{ fontWeight: 700, borderTop: '2px solid var(--color-text)' }}>
                      <td colSpan={2}>Net Income</td>
                      <td style={{ textAlign: 'right' }}>{formatCurrency(plData.net_income)}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* Balance Sheet */}
        {tab === 'bs' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <ClientSelector value={clientId} onSelect={setClientId} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)} />
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchBS} disabled={!clientId || loading}>Generate</button>
              <ExportButtons type="balance-sheet" data={bsData} />
            </div>
            {loading && !bsData && <div className="spinner" />}
            {!loading && !bsData && (
              <div className="empty-state">
                <div className="empty-state-heading">Select a client and date</div>
                <div className="empty-state-text">Click Generate to view the Balance Sheet.</div>
              </div>
            )}
            {bsData && (
              <div className="card">
                <h3 style={{ marginBottom: 16 }}>Balance Sheet — As of {formatDate(bsData.as_of_date)}</h3>
                <table className="table">
                  <thead><tr><th>Account #</th><th>Account</th><th style={{ textAlign: 'right' }}>Balance</th></tr></thead>
                  <tbody>
                    <tr style={{ fontWeight: 700 }}><td colSpan={2}>Assets</td><td style={{ textAlign: 'right' }}>{formatCurrency(bsData.total_assets)}</td></tr>
                    {renderAccountRows(bsData.assets || [])}
                    <tr style={{ fontWeight: 700 }}><td colSpan={2}>Liabilities</td><td style={{ textAlign: 'right' }}>{formatCurrency(bsData.total_liabilities)}</td></tr>
                    {renderAccountRows(bsData.liabilities || [])}
                    <tr style={{ fontWeight: 700 }}><td colSpan={2}>Equity</td><td style={{ textAlign: 'right' }}>{formatCurrency(bsData.total_equity)}</td></tr>
                    {renderAccountRows(bsData.equity || [])}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}

        {/* Cash Flow */}
        {tab === 'cf' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <ClientSelector value={clientId} onSelect={setClientId} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchCF} disabled={!clientId || loading}>Generate</button>
              <ExportButtons type="cash-flow" data={cfData} />
            </div>
            {loading && !cfData && <div className="spinner" />}
            {!loading && !cfData && (
              <div className="empty-state">
                <div className="empty-state-heading">Select a client and date range</div>
                <div className="empty-state-text">Click Generate to view the Cash Flow Statement.</div>
              </div>
            )}
            {cfData && (
              <div className="card">
                <h3 style={{ marginBottom: 16 }}>Cash Flow Statement — {formatDate(cfData.period_start)} to {formatDate(cfData.period_end)}</h3>
                {['operating', 'investing', 'financing'].map((section) => (
                  <div key={section} style={{ marginBottom: 16 }}>
                    <h4>{cfData[section]?.label}</h4>
                    <table className="table">
                      <thead><tr><th>Account #</th><th>Account</th><th style={{ textAlign: 'right' }}>Amount</th></tr></thead>
                      <tbody>
                        {renderAccountRows(cfData[section]?.items || [])}
                        <tr style={{ fontWeight: 700 }}>
                          <td colSpan={2}>Subtotal</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(cfData[section]?.subtotal)}</td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                ))}
                <div style={{ fontSize: 18, fontWeight: 700, textAlign: 'right', padding: '12px 0' }}>
                  Net Change in Cash: {formatCurrency(cfData.net_change_in_cash)}
                </div>
              </div>
            )}
          </>
        )}

        {/* Firm Dashboard */}
        {tab === 'dashboard' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={startDate} onChange={(e) => setStartDate(e.target.value)} />
              <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={endDate} onChange={(e) => setEndDate(e.target.value)} />
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchDashboard} disabled={loading}>Generate Dashboard</button>
            </div>
            {loading && !dashData && <div className="spinner" />}
            {!loading && !dashData && (
              <div className="empty-state">
                <div className="empty-state-heading">Set a date range for the dashboard</div>
                <div className="empty-state-text">Click Generate Dashboard to view firm-wide metrics.</div>
              </div>
            )}
            {dashData && (
              <>
                <div className="card-grid" style={{ marginBottom: 24 }}>
                  <div className="card"><div className="card-heading">Total Clients</div><div className="card-value">{dashData.total_clients}</div></div>
                  <div className="card"><div className="card-heading">Active Clients</div><div className="card-value">{dashData.active_clients}</div></div>
                  <div className="card"><div className="card-heading">Firm Revenue</div><div className="card-value">{formatCurrency(dashData.firm_total_revenue)}</div></div>
                  <div className="card"><div className="card-heading">Firm Expenses</div><div className="card-value">{formatCurrency(dashData.firm_total_expenses)}</div></div>
                  <div className="card"><div className="card-heading">Net Income</div><div className="card-value">{formatCurrency(dashData.firm_net_income)}</div></div>
                  <div className="card"><div className="card-heading">Total AR</div><div className="card-value">{formatCurrency(dashData.firm_total_ar)}</div></div>
                  <div className="card"><div className="card-heading">Total AP</div><div className="card-value">{formatCurrency(dashData.firm_total_ap)}</div></div>
                </div>
                {(dashData.client_metrics || []).length > 0 && (
                  <table className="table">
                    <thead>
                      <tr><th>Client</th><th>Entity</th><th>Revenue</th><th>Expenses</th><th>Net Income</th><th>AR</th><th>AP</th></tr>
                    </thead>
                    <tbody>
                      {dashData.client_metrics.map((m) => (
                        <tr key={m.client_id}>
                          <td>{m.client_name}</td>
                          <td>{m.entity_type?.replace(/_/g, ' ')}</td>
                          <td>{formatCurrency(m.total_revenue)}</td>
                          <td>{formatCurrency(m.total_expenses)}</td>
                          <td>{formatCurrency(m.net_income)}</td>
                          <td>{formatCurrency(m.total_ar_outstanding)}</td>
                          <td>{formatCurrency(m.total_ap_outstanding)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </>
            )}
          </>
        )}

        {/* AR Aging */}
        {tab === 'ar-aging' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <ClientSelector value={clientId} onSelect={setClientId} />
              <div>
                <label className="form-label">As of Date</label>
                <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)} />
              </div>
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchARaging} disabled={!clientId || loading}>Generate</button>
              <ExportButtons type="ar-aging" data={arData} />
            </div>
            {loading && !arData && <div className="spinner" />}
            {!loading && !arData && (
              <div className="empty-state">
                <div className="empty-state-heading">Select a client and as-of date</div>
                <div className="empty-state-text">Click Generate to view the AR Aging report.</div>
              </div>
            )}
            {arData && (
              <>
                <div className="card-grid" style={{ marginBottom: 24 }}>
                  <div className="card"><div className="card-heading">Total Outstanding</div><div className="card-value">{formatCurrency(arData.total_outstanding)}</div></div>
                  <div className="card"><div className="card-heading">Current</div><div className="card-value">{formatCurrency(arData.buckets?.current)}</div></div>
                  <div className="card"><div className="card-heading">1-30 Days</div><div className="card-value">{formatCurrency(arData.buckets?.days_1_30)}</div></div>
                  <div className="card"><div className="card-heading">31-60 Days</div><div className="card-value">{formatCurrency(arData.buckets?.days_31_60)}</div></div>
                  <div className="card"><div className="card-heading">61-90 Days</div><div className="card-value">{formatCurrency(arData.buckets?.days_61_90)}</div></div>
                  <div className="card"><div className="card-heading">90+ Days</div><div className="card-value">{formatCurrency(arData.buckets?.days_over_90)}</div></div>
                </div>
                <div className="card">
                  <h3 style={{ marginBottom: 16 }}>AR Aging Detail — {arData.client_name} — As of {formatDate(arData.as_of_date)}</h3>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Invoice #</th>
                        <th>Customer</th>
                        <th>Invoice Date</th>
                        <th>Due Date</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                        <th style={{ textAlign: 'right' }}>Age (Days)</th>
                        <th>Bucket</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(arData.items || []).map((item, i) => (
                        <tr key={i}>
                          <td>{item.invoice_number}</td>
                          <td>{item.customer_name}</td>
                          <td>{formatDate(item.invoice_date)}</td>
                          <td>{formatDate(item.due_date)}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                          <td style={{ textAlign: 'right' }}>{item.age_days}</td>
                          <td>{item.bucket}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(arData.items || []).length === 0 && (
                    <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>No outstanding receivables found.</p>
                  )}
                </div>
              </>
            )}
          </>
        )}

        {/* AP Aging */}
        {tab === 'ap-aging' && (
          <>
            <div style={{ display: 'flex', gap: 12, alignItems: 'flex-end', marginBottom: 16 }}>
              <ClientSelector value={clientId} onSelect={setClientId} />
              <div>
                <label className="form-label">As of Date</label>
                <input className="form-input" type="date" style={{ maxWidth: 160, marginBottom: 16 }} value={asOfDate} onChange={(e) => setAsOfDate(e.target.value)} />
              </div>
              <button className={`btn btn--primary${loading ? ' btn--loading' : ''}`} style={{ marginBottom: 16 }} onClick={fetchAPaging} disabled={!clientId || loading}>Generate</button>
              <ExportButtons type="ap-aging" data={apData} />
            </div>
            {loading && !apData && <div className="spinner" />}
            {!loading && !apData && (
              <div className="empty-state">
                <div className="empty-state-heading">Select a client and as-of date</div>
                <div className="empty-state-text">Click Generate to view the AP Aging report.</div>
              </div>
            )}
            {apData && (
              <>
                <div className="card-grid" style={{ marginBottom: 24 }}>
                  <div className="card"><div className="card-heading">Total Outstanding</div><div className="card-value">{formatCurrency(apData.total_outstanding)}</div></div>
                  <div className="card"><div className="card-heading">Current</div><div className="card-value">{formatCurrency(apData.buckets?.current)}</div></div>
                  <div className="card"><div className="card-heading">1-30 Days</div><div className="card-value">{formatCurrency(apData.buckets?.days_1_30)}</div></div>
                  <div className="card"><div className="card-heading">31-60 Days</div><div className="card-value">{formatCurrency(apData.buckets?.days_31_60)}</div></div>
                  <div className="card"><div className="card-heading">61-90 Days</div><div className="card-value">{formatCurrency(apData.buckets?.days_61_90)}</div></div>
                  <div className="card"><div className="card-heading">90+ Days</div><div className="card-value">{formatCurrency(apData.buckets?.days_over_90)}</div></div>
                </div>
                <div className="card">
                  <h3 style={{ marginBottom: 16 }}>AP Aging Detail — {apData.client_name} — As of {formatDate(apData.as_of_date)}</h3>
                  <table className="table">
                    <thead>
                      <tr>
                        <th>Bill #</th>
                        <th>Vendor</th>
                        <th>Bill Date</th>
                        <th>Due Date</th>
                        <th style={{ textAlign: 'right' }}>Amount</th>
                        <th style={{ textAlign: 'right' }}>Age (Days)</th>
                        <th>Bucket</th>
                      </tr>
                    </thead>
                    <tbody>
                      {(apData.items || []).map((item, i) => (
                        <tr key={i}>
                          <td>{item.bill_number}</td>
                          <td>{item.vendor_name}</td>
                          <td>{formatDate(item.bill_date)}</td>
                          <td>{formatDate(item.due_date)}</td>
                          <td style={{ textAlign: 'right' }}>{formatCurrency(item.amount)}</td>
                          <td style={{ textAlign: 'right' }}>{item.age_days}</td>
                          <td>{item.bucket}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {(apData.items || []).length === 0 && (
                    <p style={{ color: 'var(--color-text-muted)', marginTop: 8 }}>No outstanding payables found.</p>
                  )}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
