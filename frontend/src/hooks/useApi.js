import { useMemo } from 'react';
import axios from 'axios';
import useAuth from './useAuth';

const API_BASE = import.meta.env.VITE_API_BASE || '';

/**
 * Returns an axios instance that sends the HTTP-Only cookie
 * automatically via withCredentials: true.
 *
 * If a 401 response is received the user is logged out.
 *
 * Usage:
 *   const api = useApi();
 *   const { data } = await api.get('/api/clients');
 */
export default function useApi() {
  const { logout } = useAuth();

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
      withCredentials: true,
    });

    // Response interceptor -- auto-logout on 401
    instance.interceptors.response.use(
      (response) => response,
      (error) => {
        if (error.response && error.response.status === 401) {
          logout();
        }
        return Promise.reject(error);
      }
    );

    return instance;
  }, [logout]);

  return api;
}
