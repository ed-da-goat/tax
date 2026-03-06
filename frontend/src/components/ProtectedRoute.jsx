import { Navigate, useLocation } from 'react-router-dom';
import useAuth from '../hooks/useAuth';

/**
 * Wraps a route (or group of routes) that require authentication.
 *
 * Props:
 *   role (optional) -- if supplied, the user must hold this role.
 *                      CPA_OWNER satisfies any role requirement.
 *   children        -- the element tree to render when access is granted.
 *
 * Behaviour:
 *   - Session loading       --> show nothing (brief flash while /me resolves).
 *   - Not authenticated     --> redirect to /login (preserving intended URL).
 *   - Wrong role            --> redirect to /dashboard.
 *   - Authenticated + role  --> render children.
 */
export default function ProtectedRoute({ role, children }) {
  const { isAuthenticated, hasRole, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (role && !hasRole(role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
