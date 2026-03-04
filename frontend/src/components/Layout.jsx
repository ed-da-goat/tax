import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import RoleGate from './RoleGate';

const NAV_ITEMS = [
  { to: '/dashboard', label: 'Dashboard' },
  { to: '/clients', label: 'Clients' },
  // Builder agents will uncomment / add these as pages are built:
  // { to: '/ledger',         label: 'General Ledger' },
  // { to: '/ap',             label: 'Accounts Payable' },
  // { to: '/ar',             label: 'Accounts Receivable' },
  // { to: '/reconciliation', label: 'Bank Reconciliation' },
  // { to: '/payroll',        label: 'Payroll',          cpaOnly: true },
  // { to: '/tax-forms',      label: 'Tax Forms',        cpaOnly: true },
  // { to: '/reports',        label: 'Reports' },
  // { to: '/documents',      label: 'Documents' },
  // { to: '/admin',          label: 'Administration',   cpaOnly: true },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate('/login');
  }

  return (
    <div className="layout">
      {/* ---- Sidebar ---- */}
      <aside className="sidebar">
        <div className="sidebar-brand">
          <h2>GA&nbsp;CPA</h2>
          <span className="sidebar-subtitle">Accounting System</span>
        </div>

        <nav className="sidebar-nav">
          {NAV_ITEMS.map((item) => {
            const link = (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  'nav-link' + (isActive ? ' nav-link--active' : '')
                }
              >
                {item.label}
              </NavLink>
            );

            // If the item requires CPA_OWNER role, wrap it
            if (item.cpaOnly) {
              return (
                <RoleGate key={item.to} role="CPA_OWNER">
                  {link}
                </RoleGate>
              );
            }
            return link;
          })}
        </nav>
      </aside>

      {/* ---- Main content area ---- */}
      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left" />
          <div className="topbar-right">
            <span className="topbar-user">
              {user?.username ?? 'User'}
              <span className="topbar-role">
                {user?.role === 'CPA_OWNER' ? 'CPA Owner' : 'Associate'}
              </span>
            </span>
            <button className="btn btn--small btn--outline" onClick={handleLogout}>
              Log out
            </button>
          </div>
        </header>

        <main className="content">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
