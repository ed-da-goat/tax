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
    <div className="page">
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        Welcome back, {user?.username ?? user?.name ?? 'User'}.
      </p>

      <div className="stats-row">
        <div className="stat-card">
          <div className="stat-card-label">Active Clients</div>
          <div className="stat-card-value">
            {isLoading ? '--' : dashboard?.active_clients ?? 0}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Total Revenue</div>
          <div className="stat-card-value">
            {isLoading ? '--' : formatCurrency(dashboard?.firm_total_revenue)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Total Expenses</div>
          <div className="stat-card-value">
            {isLoading ? '--' : formatCurrency(dashboard?.firm_total_expenses)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Net Income</div>
          <div className="stat-card-value">
            {isLoading ? '--' : formatCurrency(dashboard?.firm_net_income)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Outstanding AR</div>
          <div className="stat-card-value">
            {isLoading ? '--' : formatCurrency(dashboard?.firm_total_ar)}
          </div>
        </div>
        <div className="stat-card">
          <div className="stat-card-label">Outstanding AP</div>
          <div className="stat-card-value">
            {isLoading ? '--' : formatCurrency(dashboard?.firm_total_ap)}
          </div>
        </div>
        <RoleGate role="CPA_OWNER">
          <div className="stat-card">
            <div className="stat-card-label">Pending Approvals</div>
            <div className="stat-card-value">
              {approvals?.total ?? '--'}
            </div>
          </div>
        </RoleGate>
      </div>

      <div className="section-header">
        <h2 className="section-title">Client Overview</h2>
      </div>

      <DataTable
        columns={columns}
        data={metrics.map((m) => ({ ...m, id: m.client_id }))}
        total={metrics.length}
        loading={isLoading}
        emptyMessage="No clients yet."
        onRowClick={(row) => navigate(`/clients/${row.client_id}`)}
      />
    </div>
  );
}
