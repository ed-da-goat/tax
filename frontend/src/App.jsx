import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Clients from './pages/Clients';
import ClientDetail from './pages/ClientDetail';
import JournalEntryForm from './pages/JournalEntryForm';
import ApprovalQueue from './pages/ApprovalQueue';
import AccountsPayable from './pages/AccountsPayable';
import AccountsReceivable from './pages/AccountsReceivable';
import BankReconciliation from './pages/BankReconciliation';
import Documents from './pages/Documents';
import Employees from './pages/Employees';
import Payroll from './pages/Payroll';
import Reports from './pages/Reports';
import TaxExports from './pages/TaxExports';
import TimeTracking from './pages/TimeTracking';
import Workflows from './pages/Workflows';
import ServiceBilling from './pages/ServiceBilling';
import Engagements from './pages/Engagements';
import Contacts from './pages/Contacts';
import ClientPortal from './pages/ClientPortal';
import FixedAssets from './pages/FixedAssets';
import Budgets from './pages/Budgets';
import FirmAnalytics from './pages/FirmAnalytics';
import DueDates from './pages/DueDates';

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      {/* All authenticated routes share the Layout shell */}
      <Route
        element={
          <ProtectedRoute>
            <Layout />
          </ProtectedRoute>
        }
      >
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/clients" element={<Clients />} />
        <Route path="/clients/:clientId" element={<ClientDetail />} />
        <Route path="/clients/:clientId/journal-entries/new" element={<JournalEntryForm />} />
        <Route path="/approvals" element={<ApprovalQueue />} />
        <Route path="/clients/:clientId/ap" element={<AccountsPayable />} />
        <Route path="/clients/:clientId/ar" element={<AccountsReceivable />} />
        <Route path="/reconciliation" element={<BankReconciliation />} />
        <Route path="/documents" element={<Documents />} />
        <Route path="/employees" element={<Employees />} />
        <Route path="/payroll" element={<Payroll />} />
        <Route path="/reports" element={<Reports />} />
        <Route path="/tax-exports" element={<TaxExports />} />
        <Route path="/time-tracking" element={<TimeTracking />} />
        <Route path="/workflows" element={<Workflows />} />
        <Route path="/service-billing" element={<ServiceBilling />} />
        <Route path="/engagements" element={<Engagements />} />
        <Route path="/contacts" element={<Contacts />} />
        <Route path="/portal" element={<ClientPortal />} />
        <Route path="/fixed-assets" element={<FixedAssets />} />
        <Route path="/budgets" element={<Budgets />} />
        <Route path="/analytics" element={<FirmAnalytics />} />
        <Route path="/due-dates" element={<DueDates />} />
      </Route>

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
