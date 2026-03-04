import { useMemo } from 'react';
import axios from 'axios';
import useAuth from './useAuth';

const API_BASE = 'http://localhost:8000';

/**
 * Returns an axios instance that automatically injects the JWT
 * Bearer token from AuthContext into every request.
 *
 * If a 401 response is received the user is logged out.
 *
 * Usage:
 *   const api = useApi();
 *   const { data } = await api.get('/api/clients');
 */
export default function useApi() {
  const { token, logout } = useAuth();

  const api = useMemo(() => {
    const instance = axios.create({
      baseURL: API_BASE,
      headers: {
        'Content-Type': 'application/json',
      },
    });

    // Request interceptor -- attach JWT
    instance.interceptors.request.use((config) => {
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }
      return config;
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
  }, [token, logout]);

  return api;
}
