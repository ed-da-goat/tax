import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Toast from '../components/Toast';
import { formatDate } from '../utils/format';

const PRIORITY_COLORS = { LOW: '#6B7280', MEDIUM: '#3d6d8e', HIGH: '#F59E0B', URGENT: '#EF4444' };

export default function DueDates() {
  const [toast, setToast] = useState(null);
  const [view, setView] = useState('upcoming'); // 'upcoming', 'overdue', 'all'

  const { data: reminders } = useApiQuery(['reminders'], '/api/v1/reminders');
  const markRead = useApiMutation('post', (body) => `/api/v1/reminders/${body.id}/read`, { invalidate: [['reminders']] });

  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const clientList = clients?.items || [];

  const allReminders = reminders?.items || [];
  const now = new Date();

  const filtered = allReminders.filter(r => {
    if (view === 'overdue') return new Date(r.remind_at) < now && !r.is_read;
    if (view === 'upcoming') return new Date(r.remind_at) >= now || !r.is_read;
    return true;
  });

  const sorted = [...filtered].sort((a, b) => new Date(a.remind_at) - new Date(b.remind_at));

  // Calendar view - group by month
  const byMonth = {};
  sorted.forEach(r => {
    const d = new Date(r.remind_at);
    const key = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`;
    if (!byMonth[key]) byMonth[key] = [];
    byMonth[key].push(r);
  });

  const columns = [
    { key: 'title', label: 'Reminder', render: (row) => (
      <span style={{ fontWeight: row.is_read ? 400 : 600 }}>{row.title}</span>
    )},
    { key: 'description', label: 'Description', render: (row) => row.description || '—' },
    { key: 'remind_at', label: 'Due', render: (row) => {
      const d = new Date(row.remind_at);
      const isOverdue = d < now && !row.is_read;
      return <span style={{ color: isOverdue ? '#EF4444' : undefined }}>{formatDate(row.remind_at)}</span>;
    }},
    { key: 'priority', label: 'Priority', render: (row) => (
      <span className="badge" style={{ backgroundColor: PRIORITY_COLORS[row.priority] || '#6B7280' }}>
        {row.priority || 'MEDIUM'}
      </span>
    )},
    { key: 'is_read', label: 'Status', render: (row) => row.is_read ? (
      <span style={{ color: '#10B981' }}>Done</span>
    ) : (
      <span style={{ color: '#F59E0B' }}>Pending</span>
    )},
    { key: 'actions', label: '', render: (row) => (
      !row.is_read && (
        <button className="btn btn--small btn--success" onClick={() => markRead.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Marked complete' }))}>
          Complete
        </button>
      )
    )},
  ];

  const overdueCount = allReminders.filter(r => new Date(r.remind_at) < now && !r.is_read).length;
  const upcomingCount = allReminders.filter(r => new Date(r.remind_at) >= now && !r.is_read).length;

  return (
    <div>
      <div className="page-header">
        <h1>Due Dates & Reminders</h1>
      </div>

      {/* Summary Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px', marginBottom: '24px' }}>
        <div className="stat-card" style={{ cursor: 'pointer', border: view === 'overdue' ? '2px solid #EF4444' : undefined }} onClick={() => setView('overdue')}>
          <div className="stat-card__label">Overdue</div>
          <div className="stat-card__value" style={{ color: '#EF4444' }}>{overdueCount}</div>
        </div>
        <div className="stat-card" style={{ cursor: 'pointer', border: view === 'upcoming' ? '2px solid #3d6d8e' : undefined }} onClick={() => setView('upcoming')}>
          <div className="stat-card__label">Upcoming</div>
          <div className="stat-card__value" style={{ color: '#3d6d8e' }}>{upcomingCount}</div>
        </div>
        <div className="stat-card" style={{ cursor: 'pointer', border: view === 'all' ? '2px solid #6B7280' : undefined }} onClick={() => setView('all')}>
          <div className="stat-card__label">All</div>
          <div className="stat-card__value">{allReminders.length}</div>
        </div>
      </div>

      {/* Calendar-style grouped view */}
      {Object.keys(byMonth).length > 0 ? (
        Object.entries(byMonth).map(([month, items]) => (
          <div key={month} style={{ marginBottom: '24px' }}>
            <h3 style={{ fontSize: '14px', color: '#6B7280', marginBottom: '8px', textTransform: 'uppercase' }}>
              {new Date(month + '-01').toLocaleDateString('en-US', { year: 'numeric', month: 'long' })}
            </h3>
            <DataTable columns={columns} rows={items} emptyMessage="" />
          </div>
        ))
      ) : (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
          No reminders found. Reminders are created automatically when workflow tasks have due dates.
        </div>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
