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
      </Route>

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
