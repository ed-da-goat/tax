import { createContext, useState, useCallback, useEffect } from 'react';
import axios from 'axios';

const API_BASE = 'http://localhost:8000';

/**
 * Roles defined in CLAUDE.md:
 *   CPA_OWNER  -- full access
 *   ASSOCIATE   -- restricted (cannot approve, export, finalize payroll)
 */
export const ROLES = {
  CPA_OWNER: 'CPA_OWNER',
  ASSOCIATE: 'ASSOCIATE',
};

/**
 * Decode the payload of a JWT without verifying the signature.
 * Sufficient for reading role/expiry on the client side.
 */
function decodeToken(token) {
  try {
    const payload = token.split('.')[1];
    return JSON.parse(atob(payload));
  } catch {
    return null;
  }
}

export const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [token, setToken] = useState(() => localStorage.getItem('token'));
  const [user, setUser] = useState(() => {
    const saved = localStorage.getItem('token');
    return saved ? decodeToken(saved) : null;
  });

  // Keep user object in sync whenever the token changes
  useEffect(() => {
    if (token) {
      const decoded = decodeToken(token);
      if (decoded && decoded.exp * 1000 > Date.now()) {
        setUser(decoded);
      } else {
        // Token is expired -- clear it
        logout();
      }
    }
  }, [token]);

  const login = useCallback(async (email, password) => {
    const response = await axios.post(`${API_BASE}/api/v1/auth/login`, {
      email,
      password,
    });
    const { access_token } = response.data;
    localStorage.setItem('token', access_token);
    const decoded = decodeToken(access_token);
    setUser(decoded);
    setToken(access_token);
    return decoded;
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('token');
    setToken(null);
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

  const isAuthenticated = !!token && !!user;

  const value = {
    token,
    user,
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
