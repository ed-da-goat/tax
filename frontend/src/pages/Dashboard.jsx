import useAuth from '../hooks/useAuth';
import RoleGate from '../components/RoleGate';

/**
 * Placeholder dashboard page.
 * Builder agents will replace the placeholder cards with real data
 * from the backend API as each module is completed.
 */
export default function Dashboard() {
  const { user } = useAuth();

  return (
    <div className="page">
      <h1 className="page-title">Dashboard</h1>
      <p className="page-subtitle">
        Welcome back, {user?.username ?? 'User'}.
      </p>

      <div className="card-grid">
        {/* -- Placeholder summary cards -- */}
        <div className="card">
          <h3 className="card-heading">Active Clients</h3>
          <p className="card-value">--</p>
        </div>

        <div className="card">
          <h3 className="card-heading">Pending Transactions</h3>
          <p className="card-value">--</p>
        </div>

        <div className="card">
          <h3 className="card-heading">Open Invoices</h3>
          <p className="card-value">--</p>
        </div>

        <RoleGate role="CPA_OWNER">
          <div className="card">
            <h3 className="card-heading">Awaiting Approval</h3>
            <p className="card-value">--</p>
          </div>
        </RoleGate>

        <RoleGate role="CPA_OWNER">
          <div className="card">
            <h3 className="card-heading">Upcoming Tax Deadlines</h3>
            <p className="card-value">--</p>
          </div>
        </RoleGate>
      </div>
    </div>
  );
}
