import { useState } from 'react';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import ClientSelector from '../components/ClientSelector';
import { formatCurrency } from '../utils/format';

export default function YearEndClose() {
  const api = useApi();
  const { addToast } = useToast();

  const [clientId, setClientId] = useState('');
  const [year, setYear] = useState(new Date().getFullYear() - 1);
  const [status, setStatus] = useState(null);
  const [preview, setPreview] = useState(null);
  const [loading, setLoading] = useState(false);
  const [closing, setClosing] = useState(false);
  const [reopening, setReopening] = useState(false);

  const fetchStatus = async (cid, yr) => {
    if (!cid) return;
    setLoading(true);
    setStatus(null);
    setPreview(null);
    try {
      const res = await api.get(`/api/v1/clients/${cid}/year-end/${yr}/status`);
      setStatus(res.data);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to load status');
    }
    setLoading(false);
  };

  const fetchPreview = async () => {
    setLoading(true);
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/year-end/${year}/preview`);
      setPreview(res.data);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to load preview');
    }
    setLoading(false);
  };

  const handleClose = async () => {
    setClosing(true);
    try {
      await api.post(`/api/v1/clients/${clientId}/year-end/${year}/close`);
      addToast('success', `Year ${year} closed successfully`);
      fetchStatus(clientId, year);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to close year');
    }
    setClosing(false);
  };

  const handleReopen = async () => {
    setReopening(true);
    try {
      await api.post(`/api/v1/clients/${clientId}/year-end/${year}/reopen`);
      addToast('success', `Year ${year} reopened`);
      fetchStatus(clientId, year);
    } catch (e) {
      addToast('error', e.response?.data?.detail || 'Failed to reopen year');
    }
    setReopening(false);
  };

  const handleClientChange = (cid) => {
    setClientId(cid);
    fetchStatus(cid, year);
  };

  const handleYearChange = (e) => {
    const yr = parseInt(e.target.value, 10);
    setYear(yr);
    if (clientId) fetchStatus(clientId, yr);
  };

  return (
    <RoleGate
      role="CPA_OWNER"
      fallback={
        <div className="page" style={{ maxWidth: 1000 }}>
          <div className="empty-state">
            <div className="empty-state-heading">Access Denied</div>
            <div className="empty-state-text">Year-end close requires the CPA Owner role.</div>
          </div>
        </div>
      }
    >
      <div className="page" style={{ maxWidth: 1000 }}>
        <div className="page-header">
          <h1 className="page-title">Year-End Close</h1>
        </div>

        <div className="card mb-24" style={{ padding: 16 }}>
          <div className="form-row">
            <div style={{ flex: 1 }}>
              <ClientSelector value={clientId} onChange={handleClientChange} />
            </div>
            <div style={{ width: 120 }}>
              <label style={{ fontSize: 13, fontWeight: 500 }}>
                Fiscal Year
                <input
                  className="form-input"
                  type="number"
                  value={year}
                  onChange={handleYearChange}
                  min={2020}
                  max={2099}
                  style={{ marginTop: 4 }}
                />
              </label>
            </div>
          </div>
        </div>

        {loading && <div className="spinner" />}

        {status && !loading && (
          <div className="card mb-24">
            <div className="card-heading">
              Year {year} Status: {' '}
              <span className={`badge badge--${status.is_closed ? 'inactive' : 'active'}`}>
                {status.is_closed ? 'CLOSED' : 'OPEN'}
              </span>
            </div>

            {status.closed_at && (
              <p style={{ color: '#6B7280', fontSize: 14, marginTop: 8 }}>
                Closed on: {new Date(status.closed_at).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}
              </p>
            )}

            <div style={{ display: 'flex', gap: 8, marginTop: 16 }}>
              {!status.is_closed && (
                <>
                  <button className="btn btn--outline" onClick={fetchPreview}>
                    Preview Closing Entries
                  </button>
                  <button
                    className={`btn btn--primary${closing ? ' btn--loading' : ''}`}
                    onClick={handleClose}
                    disabled={closing}
                  >
                    Close Year {year}
                  </button>
                </>
              )}
              {status.is_closed && (
                <button
                  className={`btn btn--outline${reopening ? ' btn--loading' : ''}`}
                  onClick={handleReopen}
                  disabled={reopening}
                >
                  Reopen Year {year}
                </button>
              )}
            </div>
          </div>
        )}

        {preview && (
          <div className="card">
            <div className="card-heading">Preview: Closing Entries</div>
            {preview.entries?.length > 0 ? (
              <table className="data-table" style={{ marginTop: 12 }}>
                <thead>
                  <tr>
                    <th>Account</th>
                    <th style={{ textAlign: 'right' }}>Debit</th>
                    <th style={{ textAlign: 'right' }}>Credit</th>
                  </tr>
                </thead>
                <tbody>
                  {preview.entries.map((entry, i) => (
                    <tr key={i}>
                      <td>{entry.account_name || entry.account_id}</td>
                      <td style={{ textAlign: 'right' }}>{entry.debit ? formatCurrency(entry.debit) : ''}</td>
                      <td style={{ textAlign: 'right' }}>{entry.credit ? formatCurrency(entry.credit) : ''}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p style={{ color: '#6B7280', marginTop: 8 }}>No closing entries needed.</p>
            )}
            {preview.net_income != null && (
              <p style={{ marginTop: 12, fontWeight: 600 }}>
                Net Income: {formatCurrency(preview.net_income)}
              </p>
            )}
          </div>
        )}

        {!clientId && !loading && (
          <div className="empty-state">
            <div className="empty-state-heading">Select a Client</div>
            <div className="empty-state-text">Choose a client above to manage year-end close.</div>
          </div>
        )}
      </div>
    </RoleGate>
  );
}
