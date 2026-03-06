import { useState, useEffect } from 'react';
import useApi from '../hooks/useApi';
import RoleGate from '../components/RoleGate';
import Tabs from '../components/Tabs';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';

const TABS = [
  { key: 'health', label: 'System Health' },
  { key: 'backups', label: 'Backup Management' },
  { key: 'users', label: 'Users' },
];

function formatBytes(bytes) {
  if (bytes == null) return '--';
  if (bytes === 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(1024));
  return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + units[i];
}

function formatGb(gb) {
  if (gb == null) return '--';
  return gb.toFixed(1) + ' GB';
}

function formatTimestamp(dateStr) {
  if (!dateStr) return '--';
  const d = new Date(dateStr);
  return d.toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

function StatusCard({ title, children, status }) {
  const borderColor =
    status === 'ok' ? '#10B981' : status === 'warn' ? '#F59E0B' : status === 'error' ? '#EF4444' : '#E5E7EB';
  return (
    <div className="card" style={{ borderLeft: `4px solid ${borderColor}` }}>
      <div className="card-heading">{title}</div>
      <div style={{ marginTop: 8 }}>{children}</div>
    </div>
  );
}

export default function SystemAdmin() {
  const api = useApi();
  const [tab, setTab] = useState('health');
  const [toast, setToast] = useState(null);

  // Health state
  const [health, setHealth] = useState(null);
  const [healthLoading, setHealthLoading] = useState(false);
  const [healthError, setHealthError] = useState('');

  // Backup state
  const [backups, setBackups] = useState([]);
  const [backupsTotal, setBackupsTotal] = useState(0);
  const [backupsLoading, setBackupsLoading] = useState(false);
  const [backupsError, setBackupsError] = useState('');
  const [createLoading, setCreateLoading] = useState(false);

  // Confirm restore modal
  const [restoreTarget, setRestoreTarget] = useState(null);
  const [restoring, setRestoring] = useState(false);

  // Verify state (track per filename)
  const [verifyResults, setVerifyResults] = useState({});
  const [verifying, setVerifying] = useState({});

  // Users state
  const [users, setUsers] = useState([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [usersError, setUsersError] = useState('');
  const [userModalOpen, setUserModalOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [userForm, setUserForm] = useState({ email: '', full_name: '', role: 'ASSOCIATE', password: '' });
  const [userSaving, setUserSaving] = useState(false);

  const fetchHealth = async () => {
    setHealthLoading(true);
    setHealthError('');
    try {
      const res = await api.get('/api/v1/operations/health');
      setHealth(res.data);
    } catch (e) {
      setHealthError(e.response?.data?.detail || 'Failed to load system health');
    }
    setHealthLoading(false);
  };

  const fetchBackups = async () => {
    setBackupsLoading(true);
    setBackupsError('');
    try {
      const res = await api.get('/api/v1/operations/backups');
      setBackups(res.data.backups || []);
      setBackupsTotal(res.data.total || 0);
    } catch (e) {
      setBackupsError(e.response?.data?.detail || 'Failed to load backups');
    }
    setBackupsLoading(false);
  };

  const fetchUsers = async () => {
    setUsersLoading(true);
    setUsersError('');
    try {
      const res = await api.get('/api/v1/auth/users');
      setUsers(res.data);
    } catch (e) {
      setUsersError(e.response?.data?.detail || 'Failed to load users');
    }
    setUsersLoading(false);
  };

  const openCreateUser = () => {
    setEditingUser(null);
    setUserForm({ email: '', full_name: '', role: 'ASSOCIATE', password: '' });
    setUserModalOpen(true);
  };

  const openEditUser = (user) => {
    setEditingUser(user);
    setUserForm({ email: user.email, full_name: user.full_name, role: user.role, password: '' });
    setUserModalOpen(true);
  };

  const handleSaveUser = async () => {
    setUserSaving(true);
    try {
      if (editingUser) {
        const body = { email: userForm.email, full_name: userForm.full_name, role: userForm.role };
        await api.put(`/api/v1/auth/users/${editingUser.id}`, body);
        setToast({ type: 'success', message: 'User updated' });
      } else {
        await api.post('/api/v1/auth/users', userForm);
        setToast({ type: 'success', message: 'User created' });
      }
      setUserModalOpen(false);
      fetchUsers();
    } catch (e) {
      setToast({ type: 'error', message: e.response?.data?.detail || 'Failed to save user' });
    }
    setUserSaving(false);
  };

  const handleToggleActive = async (user) => {
    try {
      await api.put(`/api/v1/auth/users/${user.id}`, { is_active: !user.is_active });
      setToast({ type: 'success', message: user.is_active ? 'User deactivated' : 'User reactivated' });
      fetchUsers();
    } catch (e) {
      setToast({ type: 'error', message: e.response?.data?.detail || 'Failed to update user' });
    }
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  useEffect(() => {
    if (tab === 'backups' && backups.length === 0 && !backupsLoading) {
      fetchBackups();
    }
    if (tab === 'users' && users.length === 0 && !usersLoading) {
      fetchUsers();
    }
  }, [tab]);

  const handleCreateBackup = async () => {
    setCreateLoading(true);
    try {
      const res = await api.post('/api/v1/operations/backup');
      setToast({ type: 'success', message: res.data.message || 'Backup created successfully' });
      fetchBackups();
    } catch (e) {
      setToast({ type: 'error', message: e.response?.data?.detail || 'Backup creation failed' });
    }
    setCreateLoading(false);
  };

  const handleVerify = async (filename) => {
    setVerifying((prev) => ({ ...prev, [filename]: true }));
    try {
      const res = await api.post(`/api/v1/operations/backups/${filename}/verify`);
      setVerifyResults((prev) => ({ ...prev, [filename]: res.data.valid }));
      setToast({
        type: res.data.valid ? 'success' : 'error',
        message: res.data.valid ? `${filename} is valid` : `${filename} is invalid`,
      });
    } catch (e) {
      setVerifyResults((prev) => ({ ...prev, [filename]: false }));
      setToast({ type: 'error', message: e.response?.data?.detail || 'Verification failed' });
    }
    setVerifying((prev) => ({ ...prev, [filename]: false }));
  };

  const handleRestore = async () => {
    if (!restoreTarget) return;
    setRestoring(true);
    try {
      const res = await api.post(`/api/v1/operations/backups/${restoreTarget}/restore`);
      setToast({ type: 'success', message: res.data.message || 'Restore completed successfully' });
      setRestoreTarget(null);
    } catch (e) {
      setToast({ type: 'error', message: e.response?.data?.detail || 'Restore failed' });
    }
    setRestoring(false);
  };

  const diskStatus = health?.disk
    ? health.disk.usage_percent > 90
      ? 'error'
      : health.disk.usage_percent > 80
        ? 'warn'
        : 'ok'
    : 'ok';

  const backupColumns = [
    { key: 'filename', label: 'Filename' },
    {
      key: 'size_bytes',
      label: 'Size',
      render: (val) => formatBytes(val),
    },
    {
      key: 'created_at',
      label: 'Created',
      render: (val) => formatTimestamp(val),
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (val, row) => (
        <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
          <button
            className={`btn btn--small btn--outline${verifying[row.filename] ? ' btn--loading' : ''}`}
            onClick={() => handleVerify(row.filename)}
            disabled={verifying[row.filename]}
          >
            {verifyResults[row.filename] === true
              ? 'Valid'
              : verifyResults[row.filename] === false
                ? 'Invalid'
                : 'Verify'}
          </button>
          <button
            className="btn btn--small btn--danger"
            onClick={() => setRestoreTarget(row.filename)}
          >
            Restore
          </button>
        </div>
      ),
    },
  ];

  return (
    <RoleGate
      role="CPA_OWNER"
      fallback={
        <div className="page" style={{ maxWidth: 1200 }}>
          <div className="empty-state">
            <div className="empty-state-heading">Access Denied</div>
            <div className="empty-state-text">System administration requires the CPA Owner role.</div>
          </div>
        </div>
      }
    >
      <div className="page" style={{ maxWidth: 1200 }}>
        <div className="page-header">
          <h1 className="page-title">System Administration</h1>
        </div>

        <Tabs tabs={TABS} activeTab={tab} onTabChange={setTab} />

        <div style={{ marginTop: 16 }}>
          {/* System Health Tab */}
          {tab === 'health' && (
            <>
              <div style={{ marginBottom: 16 }}>
                <button
                  className={`btn btn--primary${healthLoading ? ' btn--loading' : ''}`}
                  onClick={fetchHealth}
                  disabled={healthLoading}
                >
                  Refresh
                </button>
              </div>

              {healthError && (
                <div className="alert alert--error" style={{ marginBottom: 16 }}>{healthError}</div>
              )}

              {healthLoading && !health && <div className="spinner" />}

              {health && (
                <>
                  <div className="card-grid" style={{ marginBottom: 24 }}>
                    <StatusCard
                      title="Database"
                      status={health.database?.connected ? 'ok' : 'error'}
                    >
                      <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {health.database?.connected ? 'Connected' : 'Disconnected'}
                      </div>
                      {health.database?.latency_ms != null && (
                        <div style={{ color: '#6B7280', fontSize: 14, marginTop: 4 }}>
                          Latency: {health.database.latency_ms.toFixed(1)} ms
                        </div>
                      )}
                    </StatusCard>

                    <StatusCard title="Disk Usage" status={diskStatus}>
                      <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {health.disk?.usage_percent != null
                          ? health.disk.usage_percent.toFixed(1) + '%'
                          : '--'}
                      </div>
                      <div style={{ color: '#6B7280', fontSize: 14, marginTop: 4 }}>
                        {formatGb(health.disk?.free_gb)} free of {formatGb(health.disk?.total_gb)}
                      </div>
                    </StatusCard>

                    <StatusCard
                      title="Backups"
                      status={health.backups?.directory_exists ? 'ok' : 'warn'}
                    >
                      <div style={{ fontSize: 24, fontWeight: 700 }}>
                        {health.backups?.total_backups ?? 0} backups
                      </div>
                      <div style={{ color: '#6B7280', fontSize: 14, marginTop: 4 }}>
                        Last: {health.backups?.last_backup ? formatTimestamp(health.backups.last_backup) : 'Never'}
                      </div>
                      {health.backups?.last_backup_size_bytes != null && (
                        <div style={{ color: '#6B7280', fontSize: 14, marginTop: 2 }}>
                          Size: {formatBytes(health.backups.last_backup_size_bytes)}
                        </div>
                      )}
                    </StatusCard>
                  </div>

                  {/* Overall status */}
                  <div className="card" style={{ marginBottom: 16 }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <span
                        style={{
                          width: 12,
                          height: 12,
                          borderRadius: '50%',
                          backgroundColor: health.status === 'healthy' ? '#10B981' : '#F59E0B',
                          display: 'inline-block',
                        }}
                      />
                      <span style={{ fontWeight: 600, fontSize: 16 }}>
                        System Status: {health.status === 'healthy' ? 'Healthy' : health.status}
                      </span>
                    </div>
                  </div>

                  {/* Issues */}
                  {health.issues && health.issues.length > 0 && (
                    <div className="card" style={{ borderLeft: '4px solid #F59E0B' }}>
                      <div className="card-heading">Issues</div>
                      <ul style={{ margin: '8px 0 0 16px', padding: 0 }}>
                        {health.issues.map((issue, i) => (
                          <li key={i} style={{ marginBottom: 4, color: '#92400E' }}>{issue}</li>
                        ))}
                      </ul>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {/* Backups Tab */}
          {tab === 'backups' && (
            <>
              <div style={{ marginBottom: 16, display: 'flex', gap: 8 }}>
                <button
                  className={`btn btn--primary${createLoading ? ' btn--loading' : ''}`}
                  onClick={handleCreateBackup}
                  disabled={createLoading}
                >
                  Create Backup
                </button>
                <button
                  className={`btn btn--outline${backupsLoading ? ' btn--loading' : ''}`}
                  onClick={fetchBackups}
                  disabled={backupsLoading}
                >
                  Refresh
                </button>
              </div>

              {backupsError && (
                <div className="alert alert--error" style={{ marginBottom: 16 }}>{backupsError}</div>
              )}

              <DataTable
                columns={backupColumns}
                data={backups}
                total={backupsTotal}
                loading={backupsLoading}
                emptyMessage="No backups found."
              />
            </>
          )}

          {/* Users Tab */}
          {tab === 'users' && (
            <>
              <div style={{ marginBottom: 16 }}>
                <button className="btn btn--primary" onClick={openCreateUser}>
                  Add User
                </button>
              </div>

              {usersError && (
                <div className="alert alert--error" style={{ marginBottom: 16 }}>{usersError}</div>
              )}

              <DataTable
                columns={[
                  { key: 'full_name', label: 'Name' },
                  { key: 'email', label: 'Email' },
                  {
                    key: 'role',
                    label: 'Role',
                    render: (val) => val === 'CPA_OWNER' ? 'CPA Owner' : 'Associate',
                  },
                  {
                    key: 'is_active',
                    label: 'Status',
                    render: (val) => (
                      <span className={`badge badge--${val ? 'active' : 'inactive'}`}>
                        {val ? 'Active' : 'Inactive'}
                      </span>
                    ),
                  },
                  {
                    key: 'last_login_at',
                    label: 'Last Login',
                    render: (val) => formatTimestamp(val),
                  },
                  {
                    key: 'actions',
                    label: 'Actions',
                    render: (_, row) => (
                      <div style={{ display: 'flex', gap: 6 }} onClick={(e) => e.stopPropagation()}>
                        <button className="btn btn--small btn--outline" onClick={() => openEditUser(row)}>
                          Edit
                        </button>
                        <button
                          className={`btn btn--small ${row.is_active ? 'btn--danger' : 'btn--outline'}`}
                          onClick={() => handleToggleActive(row)}
                        >
                          {row.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </div>
                    ),
                  },
                ]}
                data={users}
                total={users.length}
                loading={usersLoading}
                emptyMessage="No users found."
              />
            </>
          )}
        </div>

        {/* User Create/Edit Modal */}
        <Modal
          isOpen={userModalOpen}
          title={editingUser ? 'Edit User' : 'Create User'}
          onClose={() => !userSaving && setUserModalOpen(false)}
        >
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <FormField label="Full Name">
              <input
                className="form-input"
                value={userForm.full_name}
                onChange={(e) => setUserForm({ ...userForm, full_name: e.target.value })}
              />
            </FormField>
            <FormField label="Email">
              <input
                className="form-input"
                type="email"
                value={userForm.email}
                onChange={(e) => setUserForm({ ...userForm, email: e.target.value })}
              />
            </FormField>
            <FormField label="Role">
              <select
                className="form-input form-select"
                value={userForm.role}
                onChange={(e) => setUserForm({ ...userForm, role: e.target.value })}
              >
                <option value="ASSOCIATE">Associate</option>
                <option value="CPA_OWNER">CPA Owner</option>
              </select>
            </FormField>
            {!editingUser && (
              <FormField label="Password">
                <input
                  className="form-input"
                  type="password"
                  value={userForm.password}
                  onChange={(e) => setUserForm({ ...userForm, password: e.target.value })}
                  placeholder="Min 8 chars, upper/lower/digit/special"
                />
              </FormField>
            )}
          </div>
          <div className="modal-actions" style={{ marginTop: 16 }}>
            <button className="btn btn--outline" onClick={() => setUserModalOpen(false)} disabled={userSaving}>
              Cancel
            </button>
            <button
              className={`btn btn--primary${userSaving ? ' btn--loading' : ''}`}
              onClick={handleSaveUser}
              disabled={userSaving}
            >
              {editingUser ? 'Save Changes' : 'Create User'}
            </button>
          </div>
        </Modal>

        {/* Restore Confirmation Modal */}
        <Modal
          isOpen={!!restoreTarget}
          title="Confirm Restore"
          onClose={() => !restoring && setRestoreTarget(null)}
        >
          <div style={{ marginBottom: 16 }}>
            <p style={{ marginBottom: 8 }}>
              <strong>Warning:</strong> Restoring a backup will overwrite the current database.
              This action is destructive and cannot be undone.
            </p>
            <p>
              Are you sure you want to restore from{' '}
              <strong style={{ fontFamily: 'monospace' }}>{restoreTarget}</strong>?
            </p>
          </div>
          <div className="modal-actions">
            <button
              className="btn btn--outline"
              onClick={() => setRestoreTarget(null)}
              disabled={restoring}
            >
              Cancel
            </button>
            <button
              className={`btn btn--danger${restoring ? ' btn--loading' : ''}`}
              onClick={handleRestore}
              disabled={restoring}
            >
              {restoring ? 'Restoring...' : 'Restore Backup'}
            </button>
          </div>
        </Modal>

        {toast && <Toast {...toast} onClose={() => setToast(null)} />}
      </div>
    </RoleGate>
  );
}
