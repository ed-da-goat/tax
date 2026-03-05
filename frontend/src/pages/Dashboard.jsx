import { useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import RoleGate from '../components/RoleGate';
import DataTable from '../components/DataTable';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency, formatEntityType } from '../utils/format';

export default function Dashboard() {
  const { user } = useAuth();
  const navigate = useNavigate();

  const { data: dashboard, isLoading } = useApiQuery(
    ['dashboard'],
    '/api/v1/reports/dashboard'
  );

  const { data: approvals } = useApiQuery(
    ['approvals-count'],
    '/api/v1/approvals?limit=1',
    { enabled: user?.role === 'CPA_OWNER' }
  );

  const metrics = dashboard?.client_metrics || [];
  const pendingCount = approvals?.total ?? 0;

  const columns = [
    { key: 'client_name', label: 'Client' },
    { key: 'entity_type', label: 'Type', render: (v) => formatEntityType(v) },
    { key: 'total_revenue', label: 'Revenue', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'total_expenses', label: 'Expenses', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'net_income', label: 'Net Income', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'total_ar_outstanding', label: 'AR', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
    { key: 'total_ap_outstanding', label: 'AP', render: (v) => formatCurrency(v), style: { textAlign: 'right' } },
  ];

  return (
    <div className="page" style={{ maxWidth: 1200 }}>
      <div className="page-header">
        <div>
          <h1 className="page-title">Dashboard</h1>
          <p className="page-subtitle" style={{ marginBottom: 0 }}>
            Welcome back, {user?.username ?? user?.name ?? 'User'}.
          </p>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="quick-actions" style={{ marginTop: 20 }}>
        <button className="quick-action-btn" onClick={() => navigate('/clients')}>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><circle cx="5.5" cy="5" r="2" /><path d="M1 13c0-2.2 2-4 4.5-4s4.5 1.8 4.5 4" /><path d="M11 3v6" /><path d="M8 6h6" /></svg>
          New Client
        </button>
        <RoleGate role="CPA_OWNER">
          <button
            className={`quick-action-btn${pendingCount > 0 ? ' quick-action-btn--primary' : ''}`}
            onClick={() => navigate('/approvals')}
          >
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"><path d="M3.5 8l3 3 6-6" /><circle cx="8" cy="8" r="6.5" /></svg>
            {pendingCount > 0 ? `Approve ${pendingCount} Pending` : 'Approvals'}
          </button>
        </RoleGate>
        <button className="quick-action-btn" onClick={() => navigate('/reports')}>
          <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M4 12V8" /><path d="M8 12V4" /><path d="M12 12V7" /></svg>
          Reports
        </button>
        <RoleGate role="CPA_OWNER">
          <button className="quick-action-btn" onClick={() => navigate('/payroll')}>
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><path d="M8 1v14" /><path d="M11 3.5H6.5a2 2 0 000 4h3a2 2 0 010 4H5" /></svg>
            Run Payroll
          </button>
          <button className="quick-action-btn" onClick={() => navigate('/tax-exports')}>
            <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round"><rect x="3" y="1" width="10" height="14" rx="1.5" /><path d="M6 5h4" /><path d="M6 8h4" /><path d="M6 11h2" /></svg>
            Tax Exports
          </button>
        </RoleGate>
      </div>

      {/* Stat Cards */}
      <div className="stats-row">
        <div className="stat-card stat-card--info">
          <div className="stat-card-label">Active Clients</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : dashboard?.active_clients ?? 0}
          </div>
        </div>
        <div className="stat-card stat-card--success">
          <div className="stat-card-label">Total Revenue</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : formatCurrency(dashboard?.firm_total_revenue)}
          </div>
        </div>
        <div className="stat-card stat-card--danger">
          <div className="stat-card-label">Total Expenses</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : formatCurrency(dashboard?.firm_total_expenses)}
          </div>
        </div>
        <div className="stat-card stat-card--success">
          <div className="stat-card-label">Net Income</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : formatCurrency(dashboard?.firm_net_income)}
          </div>
        </div>
        <div className="stat-card stat-card--warning stat-card--clickable" onClick={() => navigate('/clients')}>
          <div className="stat-card-label">Outstanding AR</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : formatCurrency(dashboard?.firm_total_ar)}
          </div>
        </div>
        <div className="stat-card stat-card--warning stat-card--clickable" onClick={() => navigate('/clients')}>
          <div className="stat-card-label">Outstanding AP</div>
          <div className="stat-card-value">
            {isLoading ? <span className="spinner spinner--sm" /> : formatCurrency(dashboard?.firm_total_ap)}
          </div>
        </div>
        <RoleGate role="CPA_OWNER">
          <div
            className={`stat-card stat-card--clickable${pendingCount > 0 ? ' stat-card--danger' : ' stat-card--info'}`}
            onClick={() => navigate('/approvals')}
          >
            {pendingCount > 0 && <span className="stat-card-attention" />}
            <div className="stat-card-label">Pending Approvals</div>
            <div className="stat-card-value">
              {approvals?.total ?? '--'}
            </div>
          </div>
        </RoleGate>
      </div>

      <div className="section-header">
        <h2 className="section-title">Client Overview</h2>
        <button className="btn btn--small btn--outline" onClick={() => navigate('/clients')}>
          View All
        </button>
      </div>

      <DataTable
        columns={columns}
        data={metrics.map((m) => ({ ...m, id: m.client_id }))}
        total={metrics.length}
        loading={isLoading}
        emptyMessage="No clients yet."
        emptyAction="Add your first client to get started."
        onRowClick={(row) => navigate(`/clients/${row.client_id}`)}
      />
    </div>
  );
}
