import { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency, formatDate } from '../utils/format';

const PAGE_SIZE = 25;

export default function ApprovalQueue() {
  const api = useApi();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { hasRole } = useAuth();
  const isCpa = hasRole('CPA_OWNER');

  const [page, setPage] = useState(0);
  const [selectedIds, setSelectedIds] = useState([]);

  // Rejection modal
  const [rejectTarget, setRejectTarget] = useState(null);
  const [rejectNote, setRejectNote] = useState('');

  const queryParams = new URLSearchParams({
    skip: String(page * PAGE_SIZE),
    limit: String(PAGE_SIZE),
  });

  const { data, isLoading } = useApiQuery(
    ['approvals', page],
    `/api/v1/approvals?${queryParams}`
  );

  const items = data?.items || [];

  const batchMutation = useMutation({
    mutationFn: (body) => api.post('/api/v1/approvals/batch', body),
    onSuccess: (res) => {
      const result = res.data;
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-count'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-badge'] });
      queryClient.invalidateQueries({ queryKey: ['dashboard'] });
      setSelectedIds([]);
      addToast('success', `${result.total_succeeded} of ${result.total_processed} processed`);
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Batch operation failed'),
  });

  const rejectMutation = useMutation({
    mutationFn: ({ clientId, entryId, note }) =>
      api.post(`/api/v1/clients/${clientId}/journal-entries/${entryId}/reject`, { note }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['approvals'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-count'] });
      queryClient.invalidateQueries({ queryKey: ['approvals-badge'] });
      addToast('success', 'Entry rejected');
      setRejectTarget(null);
      setRejectNote('');
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Rejection failed'),
  });

  function handleBatchApprove() {
    batchMutation.mutate({
      actions: selectedIds.map((id) => ({ entry_id: id, action: 'approve' })),
    });
  }

  function handleSingleApprove(item) {
    batchMutation.mutate({
      actions: [{ entry_id: item.id, action: 'approve' }],
    });
  }

  function handleRejectSubmit() {
    if (!rejectNote.trim()) return;
    rejectMutation.mutate({
      clientId: rejectTarget.client_id,
      entryId: rejectTarget.id,
      note: rejectNote,
    });
  }

  const columns = [
    { key: 'client_name', label: 'Client' },
    { key: 'entry_date', label: 'Date', render: (v) => formatDate(v) },
    { key: 'description', label: 'Description' },
    { key: 'reference_number', label: 'Reference' },
    {
      key: 'total_debits',
      label: 'Amount',
      render: (v) => formatCurrency(v),
      style: { textAlign: 'right' },
    },
    ...(isCpa
      ? [
          {
            key: 'actions',
            label: 'Actions',
            render: (_, row) => (
              <div style={{ display: 'flex', gap: 4 }}>
                <button
                  className="btn btn--small btn--primary"
                  onClick={(e) => { e.stopPropagation(); handleSingleApprove(row); }}
                >
                  Approve
                </button>
                <button
                  className="btn btn--small btn--danger"
                  onClick={(e) => { e.stopPropagation(); setRejectTarget(row); setRejectNote(''); }}
                >
                  Reject
                </button>
              </div>
            ),
          },
        ]
      : []),
  ];

  return (
    <div className="page">
      <div className="page-header">
        <div>
          <h1 className="page-title">Approval Queue</h1>
          <p className="text-muted">{data?.total ?? 0} entries pending approval</p>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={items}
        total={data?.total || 0}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
        loading={isLoading}
        emptyMessage="All caught up! No entries pending approval."
        emptyAction="New journal entries submitted by associates will appear here."
        selectable={isCpa}
        selectedIds={selectedIds}
        onSelectChange={setSelectedIds}
      />

      {/* Batch action bar */}
      {selectedIds.length > 0 && (
        <div className="batch-bar">
          <span className="batch-bar-count">{selectedIds.length} selected</span>
          <div className="batch-bar-actions">
            <button className="btn btn--outline" onClick={() => setSelectedIds([])}>
              Clear
            </button>
            <button
              className="btn btn--primary"
              onClick={handleBatchApprove}
              disabled={batchMutation.isPending}
            >
              Approve Selected
            </button>
          </div>
        </div>
      )}

      {/* Rejection Modal */}
      <Modal
        isOpen={!!rejectTarget}
        onClose={() => setRejectTarget(null)}
        title="Reject Entry"
        size="sm"
      >
        <p className="mb-8">
          <strong>{rejectTarget?.description || 'Journal Entry'}</strong>
        </p>
        <p className="text-muted mb-16">
          {rejectTarget?.client_name} &mdash; {formatDate(rejectTarget?.entry_date)}
        </p>
        <FormField label="Rejection Note (required)">
          <textarea
            className="form-input"
            rows={3}
            value={rejectNote}
            onChange={(e) => setRejectNote(e.target.value)}
            placeholder="Explain why this entry is being rejected..."
            autoFocus
          />
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setRejectTarget(null)}>Cancel</button>
          <button
            className="btn btn--danger"
            onClick={handleRejectSubmit}
            disabled={!rejectNote.trim() || rejectMutation.isPending}
          >
            Reject
          </button>
        </div>
      </Modal>
    </div>
  );
}
