import { useState } from 'react';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency } from '../utils/format';

function formatHours(mins) {
  if (!mins) return '0h';
  const h = Math.floor(mins / 60);
  const m = mins % 60;
  return m ? `${h}h ${m}m` : `${h}h`;
}

export default function FirmAnalytics() {
  const today = new Date();
  const yearStart = `${today.getFullYear()}-01-01`;
  const todayStr = today.toISOString().split('T')[0];

  const [dateFrom, setDateFrom] = useState(yearStart);
  const [dateTo, setDateTo] = useState(todayStr);

  const { data: dashboard } = useApiQuery(
    ['analytics-dashboard', dateFrom, dateTo],
    `/api/v1/analytics/dashboard?date_from=${dateFrom}&date_to=${dateTo}`
  );
  const { data: revenue } = useApiQuery(
    ['analytics-revenue', dateFrom, dateTo],
    `/api/v1/analytics/revenue-by-service?date_from=${dateFrom}&date_to=${dateTo}`
  );
  const { data: profitability } = useApiQuery(
    ['analytics-profitability', dateFrom, dateTo],
    `/api/v1/analytics/client-profitability?date_from=${dateFrom}&date_to=${dateTo}`
  );
  const { data: wip } = useApiQuery(['analytics-wip'], '/api/v1/analytics/wip');
  const { data: realization } = useApiQuery(
    ['analytics-realization', dateFrom, dateTo],
    `/api/v1/analytics/realization?date_from=${dateFrom}&date_to=${dateTo}`
  );

  return (
    <div>
      <div className="page-header">
        <h1>Firm Analytics</h1>
        <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
          <input type="date" value={dateFrom} onChange={e => setDateFrom(e.target.value)} />
          <span>to</span>
          <input type="date" value={dateTo} onChange={e => setDateTo(e.target.value)} />
        </div>
      </div>

      {/* KPI Cards */}
      {dashboard && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px', marginBottom: '24px' }}>
          <div className="stat-card">
            <div className="stat-card__label">Total Revenue</div>
            <div className="stat-card__value">{formatCurrency(dashboard.total_revenue || 0)}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__label">Active Clients</div>
            <div className="stat-card__value">{dashboard.active_clients || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__label">Open Workflows</div>
            <div className="stat-card__value">{dashboard.open_workflows || 0}</div>
          </div>
          <div className="stat-card">
            <div className="stat-card__label">Billable Hours</div>
            <div className="stat-card__value">{formatHours(dashboard.billable_minutes || 0)}</div>
          </div>
        </div>
      )}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
        {/* Revenue by Service */}
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Revenue by Service Type</h2>
          {(revenue || []).length === 0 ? (
            <p style={{ color: '#6B7280' }}>No revenue data for this period</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '6px', textAlign: 'left' }}>Service</th>
                  <th style={{ padding: '6px', textAlign: 'right' }}>Hours</th>
                  <th style={{ padding: '6px', textAlign: 'right' }}>Revenue</th>
                </tr>
              </thead>
              <tbody>
                {(revenue || []).map((r, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '6px' }}>{r.service_type || 'Unclassified'}</td>
                    <td style={{ padding: '6px', textAlign: 'right' }}>{r.total_hours?.toFixed(1) || '0'}</td>
                    <td style={{ padding: '6px', textAlign: 'right' }}>{formatCurrency(r.total_revenue || 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* WIP Summary */}
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Work in Progress</h2>
          {!wip ? (
            <p style={{ color: '#6B7280' }}>Loading...</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Unbilled Hours</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{formatHours(wip.unbilled_minutes || 0)}</div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Unbilled Amount</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{formatCurrency(wip.unbilled_amount || 0)}</div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Draft Entries</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{wip.draft_count || 0}</div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Pending Approval</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{wip.submitted_count || 0}</div>
              </div>
            </div>
          )}
        </div>

        {/* Client Profitability */}
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Client Profitability</h2>
          {(profitability || []).length === 0 ? (
            <p style={{ color: '#6B7280' }}>No data for this period</p>
          ) : (
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '6px', textAlign: 'left' }}>Client</th>
                  <th style={{ padding: '6px', textAlign: 'right' }}>Revenue</th>
                  <th style={{ padding: '6px', textAlign: 'right' }}>Hours</th>
                  <th style={{ padding: '6px', textAlign: 'right' }}>Eff. Rate</th>
                </tr>
              </thead>
              <tbody>
                {(profitability || []).map((p, i) => (
                  <tr key={i} style={{ borderBottom: '1px solid #e5e7eb' }}>
                    <td style={{ padding: '6px' }}>{p.client_name || 'Unknown'}</td>
                    <td style={{ padding: '6px', textAlign: 'right' }}>{formatCurrency(p.total_revenue || 0)}</td>
                    <td style={{ padding: '6px', textAlign: 'right' }}>{p.total_hours?.toFixed(1) || '0'}</td>
                    <td style={{ padding: '6px', textAlign: 'right' }}>{formatCurrency(p.effective_rate || 0)}/hr</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Realization Rate */}
        <div style={{ backgroundColor: 'white', borderRadius: '8px', padding: '20px', boxShadow: '0 1px 3px rgba(0,0,0,0.1)' }}>
          <h2 style={{ fontSize: '16px', marginBottom: '16px' }}>Realization Rate</h2>
          {!realization ? (
            <p style={{ color: '#6B7280' }}>Loading...</p>
          ) : (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Standard Billing</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{formatCurrency(realization.standard_billing || 0)}</div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Collected</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{formatCurrency(realization.collected || 0)}</div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Realization Rate</div>
                <div style={{ fontSize: '24px', fontWeight: 600, color: parseFloat(realization.rate || 0) >= 90 ? '#10B981' : '#F59E0B' }}>
                  {parseFloat(realization.rate || 0).toFixed(1)}%
                </div>
              </div>
              <div>
                <div style={{ color: '#6B7280', fontSize: '12px' }}>Write-offs</div>
                <div style={{ fontSize: '24px', fontWeight: 600 }}>{formatCurrency(realization.write_offs || 0)}</div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
