import { Routes, Route, Navigate } from 'react-router-dom';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Clients from './pages/Clients';

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

        {/* Placeholder routes -- builder agents will add pages */}
        {/* <Route path="/clients/:id" element={<ClientDetail />} /> */}
        {/* <Route path="/ledger" element={<GeneralLedger />} /> */}
        {/* <Route path="/ap" element={<AccountsPayable />} /> */}
        {/* <Route path="/ar" element={<AccountsReceivable />} /> */}
        {/* <Route path="/reconciliation" element={<BankReconciliation />} /> */}
        {/* <Route path="/payroll" element={<Payroll />} /> */}
        {/* <Route path="/tax-forms" element={<TaxForms />} /> */}
        {/* <Route path="/reports" element={<Reports />} /> */}
        {/* <Route path="/documents" element={<Documents />} /> */}
        {/* <Route path="/admin" element={<Admin />} /> */}
      </Route>

      {/* Default redirect */}
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
