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
 *   - Not authenticated  --> redirect to /login (preserving intended URL).
 *   - Authenticated but wrong role --> redirect to /dashboard.
 *   - Authenticated with correct role --> render children.
 */
export default function ProtectedRoute({ role, children }) {
  const { isAuthenticated, hasRole } = useAuth();
  const location = useLocation();

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  if (role && !hasRole(role)) {
    return <Navigate to="/dashboard" replace />;
  }

  return children;
}
