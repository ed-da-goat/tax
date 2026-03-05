import { Outlet, NavLink, useNavigate } from 'react-router-dom';
import useAuth from '../hooks/useAuth';
import RoleGate from './RoleGate';
import { useApiQuery } from '../hooks/useApiQuery';

/* ---- SVG Nav Icons (18×18, stroke-based) ---- */
const icons = {
  dashboard: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="1.5" width="6" height="6" rx="1" />
      <rect x="10.5" y="1.5" width="6" height="6" rx="1" />
      <rect x="1.5" y="10.5" width="6" height="6" rx="1" />
      <rect x="10.5" y="10.5" width="6" height="6" rx="1" />
    </svg>
  ),
  clients: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="6.5" cy="5" r="2.5" />
      <path d="M1.5 15.5c0-2.76 2.24-5 5-5s5 2.24 5 5" />
      <circle cx="13" cy="6" r="2" />
      <path d="M13.5 10.5c1.93.5 3 2.24 3 4.5" />
    </svg>
  ),
  approvals: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.5 9l3 3 6-6" />
      <circle cx="9" cy="9" r="7.5" />
    </svg>
  ),
  bank: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M2 7.5L9 3l7 4.5" />
      <path d="M3.5 7.5v6" /><path d="M7 7.5v6" /><path d="M11 7.5v6" /><path d="M14.5 7.5v6" />
      <path d="M1.5 14.5h15" />
    </svg>
  ),
  documents: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M10.5 1.5H4.5a1.5 1.5 0 0 0-1.5 1.5v12a1.5 1.5 0 0 0 1.5 1.5h9a1.5 1.5 0 0 0 1.5-1.5v-9l-4.5-4.5z" />
      <path d="M10.5 1.5v4.5h4.5" />
    </svg>
  ),
  employees: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="5.5" r="3" />
      <path d="M2 16.5c0-3.31 3.13-6 7-6s7 2.69 7 6" />
    </svg>
  ),
  payroll: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M9 1.5v15" />
      <path d="M12.5 4.5h-5.25a2.25 2.25 0 0 0 0 4.5h3.5a2.25 2.25 0 0 1 0 4.5H5" />
    </svg>
  ),
  reports: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M4.5 13.5v-4" /><path d="M9 13.5v-8" /><path d="M13.5 13.5v-6" />
      <rect x="1.5" y="1.5" width="15" height="15" rx="1.5" />
    </svg>
  ),
  tax: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="1.5" width="12" height="15" rx="1.5" />
      <path d="M6 5.5h6" /><path d="M6 8.5h6" /><path d="M6 11.5h3" />
    </svg>
  ),
  time: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="7.5" />
      <path d="M9 4.5v4.5l3 1.5" />
    </svg>
  ),
  workflow: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="2" width="5" height="4" rx="1" />
      <rect x="11.5" y="2" width="5" height="4" rx="1" />
      <rect x="6.5" y="12" width="5" height="4" rx="1" />
      <path d="M4 6v3h10V6" /><path d="M9 9v3" />
    </svg>
  ),
  billing: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="14" height="12" rx="1.5" />
      <path d="M2 7.5h14" /><path d="M5.5 11h3" />
    </svg>
  ),
  engagement: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H4a1.5 1.5 0 0 0-1.5 1.5v11A1.5 1.5 0 0 0 4 16h10a1.5 1.5 0 0 0 1.5-1.5v-11A1.5 1.5 0 0 0 14 2z" />
      <path d="M6 6h6" /><path d="M6 9h4" /><path d="M6 12h2" />
      <path d="M11 11l1.5 1.5L15 10" />
    </svg>
  ),
  contacts: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="3" y="1.5" width="12" height="15" rx="1.5" />
      <circle cx="9" cy="7" r="2.5" />
      <path d="M5.5 13.5c0-1.66 1.57-3 3.5-3s3.5 1.34 3.5 3" />
    </svg>
  ),
  portal: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="14" height="12" rx="2" />
      <path d="M6 8h6" /><path d="M6 11h4" />
    </svg>
  ),
  assets: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="1.5" y="6" width="15" height="10" rx="1.5" />
      <path d="M4.5 6V4.5a3 3 0 0 1 3-3h3a3 3 0 0 1 3 3V6" />
      <circle cx="9" cy="11" r="2" />
    </svg>
  ),
  budget: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <path d="M1.5 14.5h15" /><path d="M1.5 1.5v13" />
      <path d="M4 11l3-4 3 2 4-5" />
    </svg>
  ),
  analytics: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <circle cx="9" cy="9" r="7.5" />
      <path d="M9 1.5v7.5l5.3 5.3" />
      <path d="M9 9l-5.3 5.3" />
    </svg>
  ),
  calendar: (
    <svg className="nav-icon" viewBox="0 0 18 18" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round">
      <rect x="2" y="3" width="14" height="13" rx="1.5" />
      <path d="M2 7.5h14" /><path d="M6 1.5v3" /><path d="M12 1.5v3" />
    </svg>
  ),
};

const NAV_SECTIONS = [
  {
    label: 'Overview',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: 'dashboard' },
      { to: '/clients', label: 'Clients', icon: 'clients' },
      { to: '/analytics', label: 'Firm Analytics', icon: 'analytics', cpaOnly: true },
    ],
  },
  {
    label: 'Financial',
    items: [
      { to: '/approvals', label: 'Approvals', icon: 'approvals', cpaOnly: true, showBadge: true },
      { to: '/reconciliation', label: 'Bank Recon', icon: 'bank' },
      { to: '/service-billing', label: 'Billing', icon: 'billing' },
      { to: '/budgets', label: 'Budgets', icon: 'budget' },
      { to: '/fixed-assets', label: 'Fixed Assets', icon: 'assets' },
      { to: '/documents', label: 'Documents', icon: 'documents' },
    ],
  },
  {
    label: 'Practice',
    items: [
      { to: '/time-tracking', label: 'Time Tracking', icon: 'time' },
      { to: '/workflows', label: 'Workflows', icon: 'workflow' },
      { to: '/engagements', label: 'Engagements', icon: 'engagement' },
      { to: '/contacts', label: 'Contacts', icon: 'contacts' },
      { to: '/due-dates', label: 'Due Dates', icon: 'calendar' },
    ],
  },
  {
    label: 'Operations',
    items: [
      { to: '/employees', label: 'Employees', icon: 'employees' },
      { to: '/payroll', label: 'Payroll', icon: 'payroll', cpaOnly: true },
      { to: '/reports', label: 'Reports', icon: 'reports' },
      { to: '/tax-exports', label: 'Tax Exports', icon: 'tax', cpaOnly: true },
    ],
  },
  {
    label: 'Client Portal',
    items: [
      { to: '/portal', label: 'Portal Admin', icon: 'portal', cpaOnly: true },
    ],
  },
];

export default function Layout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Fetch pending approval count for the nav badge
  const { data: approvals } = useApiQuery(
    ['approvals-badge'],
    '/api/v1/approvals?limit=1',
    { enabled: user?.role === 'CPA_OWNER', refetchInterval: 30000 }
  );
  const pendingCount = approvals?.total ?? 0;

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
          {NAV_SECTIONS.map((section) => (
            <div key={section.label} className="sidebar-section">
              <span className="sidebar-section-label">{section.label}</span>
              {section.items.map((item) => {
                const link = (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    className={({ isActive }) =>
                      'nav-link' + (isActive ? ' nav-link--active' : '')
                    }
                  >
                    {icons[item.icon]}
                    {item.label}
                    {item.showBadge && pendingCount > 0 && (
                      <span className="nav-badge">{pendingCount}</span>
                    )}
                  </NavLink>
                );

                if (item.cpaOnly) {
                  return (
                    <RoleGate key={item.to} role="CPA_OWNER">
                      {link}
                    </RoleGate>
                  );
                }
                return link;
              })}
            </div>
          ))}
        </nav>

        <div className="sidebar-footer">v1.0 &middot; Georgia CPA Firm</div>
      </aside>

      {/* ---- Main content area ---- */}
      <div className="main-area">
        <header className="topbar">
          <div className="topbar-left" />
          <div className="topbar-right">
            <span className="topbar-user">
              {user?.full_name ?? 'User'}
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
