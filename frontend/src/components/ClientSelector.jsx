import { useState, useEffect } from 'react';
import useApi from '../hooks/useApi';

/**
 * Reusable client dropdown.
 * Fetches client list from API and calls onSelect(clientId) on change.
 */
export default function ClientSelector({ value, onSelect, className = '' }) {
  const api = useApi();
  const [clients, setClients] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    api
      .get('/api/v1/clients', { params: { limit: 100 } })
      .then((res) => {
        if (!cancelled) {
          const items = res.data.items || res.data || [];
          setClients(items);
          // Auto-select first client if none selected
          if (!value && items.length > 0) {
            onSelect(items[0].id);
          }
        }
      })
      .catch(() => {})
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <select
      className={`form-input form-select ${className}`}
      style={{ maxWidth: 300, marginBottom: 16 }}
      value={value || ''}
      onChange={(e) => onSelect(e.target.value)}
      disabled={loading}
    >
      {loading && <option value="">Loading clients...</option>}
      {!loading && clients.length === 0 && <option value="">No clients</option>}
      {clients.map((c) => (
        <option key={c.id} value={c.id}>
          {c.name} ({c.entity_type?.replace(/_/g, ' ') || 'Unknown'})
        </option>
      ))}
    </select>
  );
}
