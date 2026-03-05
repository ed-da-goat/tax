import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import useAuth from '../hooks/useAuth';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import RoleGate from '../components/RoleGate';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import StatusBadge from '../components/StatusBadge';
import { FormField, SelectField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatEntityType } from '../utils/format';

const ENTITY_TYPES = [
  { value: 'SOLE_PROP', label: 'Sole Proprietor' },
  { value: 'S_CORP', label: 'S-Corp' },
  { value: 'C_CORP', label: 'C-Corp' },
  { value: 'PARTNERSHIP_LLC', label: 'Partnership / LLC' },
];

const PAGE_SIZE = 25;

const emptyForm = {
  name: '',
  entity_type: '',
  address: '',
  phone: '',
  email: '',
};

export default function Clients() {
  const navigate = useNavigate();
  const api = useApi();
  const queryClient = useQueryClient();
  const { addToast } = useToast();
  const { hasRole } = useAuth();

  const [page, setPage] = useState(0);
  const [entityFilter, setEntityFilter] = useState('');
  const [search, setSearch] = useState('');
  const [showArchived, setShowArchived] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editingClient, setEditingClient] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});

  const [archiveTarget, setArchiveTarget] = useState(null);

  const queryParams = new URLSearchParams({
    skip: String(page * PAGE_SIZE),
    limit: String(PAGE_SIZE),
  });
  if (entityFilter) queryParams.set('entity_type', entityFilter);
  if (!showArchived) queryParams.set('is_active', 'true');

  const { data, isLoading } = useApiQuery(
    ['clients', { page, entityFilter, showArchived }],
    `/api/v1/clients?${queryParams}`
  );

  const clients = (data?.items || []).filter((c) =>
    !search || c.name.toLowerCase().includes(search.toLowerCase())
  );

  const createMutation = useMutation({
    mutationFn: (body) => api.post('/api/v1/clients', body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      addToast('success', 'Client created');
      closeModal();
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to create client'),
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, body }) => api.put(`/api/v1/clients/${id}`, body),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      addToast('success', 'Client updated');
      closeModal();
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to update client'),
  });

  const archiveMutation = useMutation({
    mutationFn: (id) => api.delete(`/api/v1/clients/${id}`),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['clients'] });
      addToast('success', 'Client archived');
      setArchiveTarget(null);
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to archive client'),
  });

  function openCreate() {
    setEditingClient(null);
    setForm(emptyForm);
    setErrors({});
    setModalOpen(true);
  }

  function openEdit(client) {
    setEditingClient(client);
    setForm({
      name: client.name || '',
      entity_type: client.entity_type || '',
      ein: client.ein || '',
      address: client.address || '',
      phone: client.phone || '',
      email: client.email || '',
    });
    setErrors({});
    setModalOpen(true);
  }

  function closeModal() {
    setModalOpen(false);
    setEditingClient(null);
  }

  function handleChange(e) {
    setForm({ ...form, [e.target.name]: e.target.value });
  }

  function handleSubmit(e) {
    e.preventDefault();
    const errs = {};
    if (!form.name.trim()) errs.name = 'Name is required';
    if (!form.entity_type) errs.entity_type = 'Entity type is required';
    if (Object.keys(errs).length > 0) {
      setErrors(errs);
      return;
    }
    if (editingClient) {
      updateMutation.mutate({ id: editingClient.id, body: form });
    } else {
      createMutation.mutate(form);
    }
  }

  const columns = [
    { key: 'name', label: 'Name' },
    { key: 'entity_type', label: 'Entity Type', render: (v) => formatEntityType(v) },
    { key: 'phone', label: 'Phone' },
    { key: 'email', label: 'Email' },
    {
      key: 'deleted_at',
      label: 'Status',
      render: (v) => <StatusBadge status={v ? 'ARCHIVED' : 'ACTIVE'} />,
    },
    {
      key: 'actions',
      label: 'Actions',
      render: (_, row) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button
            className="btn btn--small btn--outline"
            onClick={(e) => { e.stopPropagation(); navigate(`/clients/${row.id}`); }}
          >
            View
          </button>
          <RoleGate role="CPA_OWNER">
            <button
              className="btn btn--small btn--outline"
              onClick={(e) => { e.stopPropagation(); openEdit(row); }}
            >
              Edit
            </button>
            {!row.deleted_at && (
              <button
                className="btn btn--small btn--danger"
                onClick={(e) => { e.stopPropagation(); setArchiveTarget(row); }}
              >
                Archive
              </button>
            )}
          </RoleGate>
        </div>
      ),
    },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Clients</h1>
        <RoleGate role="CPA_OWNER">
          <button className="btn btn--primary" onClick={openCreate}>
            Add Client
          </button>
        </RoleGate>
      </div>

      <div className="filter-bar">
        <div className="form-field">
          <input
            className="form-input"
            type="text"
            placeholder="Search by name..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
          />
        </div>
        <div className="form-field">
          <select
            className="form-input form-select"
            value={entityFilter}
            onChange={(e) => { setEntityFilter(e.target.value); setPage(0); }}
          >
            <option value="">All Types</option>
            {ENTITY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
        <div className="form-field">
          <label style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13 }}>
            <input
              type="checkbox"
              checked={showArchived}
              onChange={(e) => { setShowArchived(e.target.checked); setPage(0); }}
            />
            Show archived
          </label>
        </div>
      </div>

      <DataTable
        columns={columns}
        data={clients}
        total={data?.total || 0}
        page={page}
        pageSize={PAGE_SIZE}
        onPageChange={setPage}
        loading={isLoading}
        emptyMessage="No clients found."
        onRowClick={(row) => navigate(`/clients/${row.id}`)}
      />

      {/* Create/Edit Modal */}
      <Modal
        isOpen={modalOpen}
        onClose={closeModal}
        title={editingClient ? 'Edit Client' : 'Add Client'}
        size="md"
      >
        <form onSubmit={handleSubmit}>
          <FormField label="Name" error={errors.name} required>
            <input
              className="form-input"
              name="name"
              value={form.name}
              onChange={handleChange}
              autoFocus
              placeholder="Business or individual name"
            />
          </FormField>

          <SelectField
            label="Entity Type"
            name="entity_type"
            value={form.entity_type}
            onChange={handleChange}
            options={ENTITY_TYPES}
            placeholder="Select type..."
            error={errors.entity_type}
            required
          />

          <FormField label="EIN">
            <input
              className="form-input"
              name="ein"
              value={form.ein}
              onChange={handleChange}
              placeholder="XX-XXXXXXX"
            />
          </FormField>

          <FormField label="Address">
            <input
              className="form-input"
              name="address"
              value={form.address}
              onChange={handleChange}
            />
          </FormField>

          <div className="form-row">
            <FormField label="Phone">
              <input
                className="form-input"
                name="phone"
                value={form.phone}
                onChange={handleChange}
              />
            </FormField>
            <FormField label="Email">
              <input
                className="form-input"
                name="email"
                type="email"
                value={form.email}
                onChange={handleChange}
              />
            </FormField>
          </div>

          <div className="form-actions">
            <button type="button" className="btn btn--outline" onClick={closeModal}>
              Cancel
            </button>
            <button
              type="submit"
              className="btn btn--primary"
              disabled={createMutation.isPending || updateMutation.isPending}
            >
              {editingClient ? 'Save Changes' : 'Create Client'}
            </button>
          </div>
        </form>
      </Modal>

      {/* Archive Confirmation */}
      <ConfirmDialog
        isOpen={!!archiveTarget}
        onCancel={() => setArchiveTarget(null)}
        onConfirm={() => archiveMutation.mutate(archiveTarget.id)}
        title="Archive Client"
        message={`Are you sure you want to archive "${archiveTarget?.name}"? This can be undone later.`}
        confirmLabel="Archive"
      />
    </div>
  );
}
