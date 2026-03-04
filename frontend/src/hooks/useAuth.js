import { useContext } from 'react';
import { AuthContext } from '../contexts/AuthContext';

/**
 * Convenience hook for consuming AuthContext.
 *
 * Usage:
 *   const { user, login, logout, isCpaOwner, isAssociate, hasRole } = useAuth();
 */
export default function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an <AuthProvider>');
  }
  return context;
}
