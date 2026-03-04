import useAuth from '../hooks/useAuth';

/**
 * Conditionally renders children based on the current user's role.
 *
 * Props:
 *   role     -- required role string ('CPA_OWNER' or 'ASSOCIATE').
 *               CPA_OWNER satisfies any role requirement.
 *   fallback -- (optional) element to render when the role check fails.
 *               Defaults to null (render nothing).
 *
 * Usage:
 *   <RoleGate role="CPA_OWNER">
 *     <button>Approve Transaction</button>
 *   </RoleGate>
 *
 *   <RoleGate role="CPA_OWNER" fallback={<span>Approval pending</span>}>
 *     <button>Approve Transaction</button>
 *   </RoleGate>
 */
export default function RoleGate({ role, fallback = null, children }) {
  const { hasRole } = useAuth();

  if (!hasRole(role)) {
    return fallback;
  }

  return children;
}
