import { createContext, useState, useCallback, useEffect } from 'react';
import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_BASE || '';

/**
 * Roles defined in CLAUDE.md:
 *   CPA_OWNER  -- full access
 *   ASSOCIATE   -- restricted (cannot approve, export, finalize payroll)
 */
export const ROLES = {
  CPA_OWNER: 'CPA_OWNER',
  ASSOCIATE: 'ASSOCIATE',
};

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // On mount, check if we have a valid session by calling /api/v1/auth/me.
  // The HTTP-Only cookie is sent automatically by the browser.
  useEffect(() => {
    axios
      .get(`${API_BASE}/api/v1/auth/me`, { withCredentials: true })
      .then((res) => {
        setUser(res.data);
      })
      .catch(() => {
        setUser(null);
      })
      .finally(() => {
        setLoading(false);
      });
  }, []);

  const login = useCallback(async (email, password, totp_code) => {
    const body = { email, password };
    if (totp_code) body.totp_code = totp_code;
    const response = await axios.post(
      `${API_BASE}/api/v1/auth/login`,
      body,
      { withCredentials: true }
    );
    // Check if 2FA is required
    if (response.data.requires_2fa) {
      return { requires_2fa: true, user: response.data.user };
    }
    // Backend sets HTTP-Only cookie. We read user info from body.
    const userData = response.data.user;
    setUser(userData);
    return userData;
  }, []);

  const logout = useCallback(async () => {
    try {
      await axios.post(
        `${API_BASE}/api/v1/auth/logout`,
        {},
        { withCredentials: true }
      );
    } catch {
      // Logout best-effort — cookie may already be expired
    }
    setUser(null);
  }, []);

  // --------------- Role helpers ---------------

  const isCpaOwner = useCallback(() => {
    return user?.role === ROLES.CPA_OWNER;
  }, [user]);

  const isAssociate = useCallback(() => {
    return user?.role === ROLES.ASSOCIATE;
  }, [user]);

  const hasRole = useCallback(
    (role) => {
      if (role === ROLES.ASSOCIATE) {
        // Both CPA_OWNER and ASSOCIATE satisfy an ASSOCIATE requirement
        return !!user;
      }
      return user?.role === role;
    },
    [user]
  );

  const isAuthenticated = !!user;

  const value = {
    user,
    loading,
    isAuthenticated,
    login,
    logout,
    isCpaOwner,
    isAssociate,
    hasRole,
    ROLES,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
