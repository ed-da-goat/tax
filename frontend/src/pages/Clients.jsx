import { useState } from 'react';

/**
 * Placeholder clients list page.
 * Builder agents will connect this to the /api/clients endpoint
 * and add create / edit / archive functionality.
 */
export default function Clients() {
  const [search, setSearch] = useState('');

  // Placeholder data -- replaced by API call once backend is ready
  const clients = [];

  const filtered = clients.filter((c) =>
    c.name.toLowerCase().includes(search.toLowerCase())
  );

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Clients</h1>
        {/* Button will be wired up by builder agent */}
        <button className="btn btn--primary" disabled>
          Add Client
        </button>
      </div>

      <input
        className="form-input search-input"
        type="text"
        placeholder="Search clients..."
        value={search}
        onChange={(e) => setSearch(e.target.value)}
      />

      {filtered.length === 0 ? (
        <p className="empty-state">
          No clients found. Connect the backend API to load client data.
        </p>
      ) : (
        <table className="table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Entity Type</th>
              <th>Status</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((c) => (
              <tr key={c.id}>
                <td>{c.name}</td>
                <td>{c.entity_type}</td>
                <td>{c.status}</td>
                <td>
                  <button className="btn btn--small">View</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
