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

  const fetchPL = async () => {
    if (!clientId) return;
    setLoading(true); setError('');
    try {
      const res = await api.get(`/api/v1/reports/clients/${clientId}/profit-loss`, {
        params: { start_date: startDate, end_date: endDate },
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
        params: { start_date: startDate, end_date: endDate },
      });
      setCfData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load report'); }
    setLoading(false);
  };

  const fetchDashboard = async () => {
    setLoading(true); setError('');
    try {
      const res = await api.get('/api/v1/reports/dashboard', {
        params: { start_date: startDate, end_date: endDate },
      });
      setDashData(res.data);
    } catch (e) { setError(e.response?.data?.detail || 'Failed to load dashboard'); }
    setLoading(false);
  };

  const exportPdf = async (type) => {
    if (!clientId) return;
    try {
      const params = type === 'balance-sheet'
        ? { as_of_date: asOfDate }
        : { start_date: startDate, end_date: endDate };
      const res = await api.get(`/api/v1/reports/clients/${clientId}/${type}/pdf`, {
        params,
        responseType: 'blob',
      });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: 'application/pdf' }));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', `${type}-${clientId}.pdf`);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || 'PDF export failed');
    }
  };

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
              <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={fetchPL} disabled={!clientId || loading}>Generate</button>
              <RoleGate role="CPA_OWNER">
                {plData && <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportPdf('profit-loss')}>Export PDF</button>}
              </RoleGate>
            </div>
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
              <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={fetchBS} disabled={!clientId || loading}>Generate</button>
              <RoleGate role="CPA_OWNER">
                {bsData && <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportPdf('balance-sheet')}>Export PDF</button>}
              </RoleGate>
            </div>
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
              <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={fetchCF} disabled={!clientId || loading}>Generate</button>
              <RoleGate role="CPA_OWNER">
                {cfData && <button className="btn btn--outline" style={{ marginBottom: 16 }} onClick={() => exportPdf('cash-flow')}>Export PDF</button>}
              </RoleGate>
            </div>
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
              <button className="btn btn--primary" style={{ marginBottom: 16 }} onClick={fetchDashboard} disabled={loading}>Generate Dashboard</button>
            </div>
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
      </div>
    </div>
  );
}
