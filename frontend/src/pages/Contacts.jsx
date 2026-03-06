import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Toast from '../components/Toast';

export default function Contacts() {
  const [toast, setToast] = useState(null);
  const [showAdd, setShowAdd] = useState(false);
  const [editContact, setEditContact] = useState(null);
  const [filters, setFilters] = useState({ client_id: '', search: '' });

  const params = new URLSearchParams();
  if (filters.client_id) params.set('client_id', filters.client_id);
  if (filters.search) params.set('search', filters.search);

  const { data } = useApiQuery(['contacts', filters], `/api/v1/contacts?${params}`);
  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');

  const createContact = useApiMutation('post', '/api/v1/contacts', { invalidate: [['contacts']] });
  const updateContact = useApiMutation('put', (body) => `/api/v1/contacts/${body.id}`, { invalidate: [['contacts']] });
  const deleteContact = useApiMutation('delete', (body) => `/api/v1/contacts/${body.id}`, { invalidate: [['contacts']] });

  const emptyForm = {
    client_id: '', first_name: '', last_name: '', email: '', phone: '', mobile: '',
    title: '', is_primary: false, address: '', city: '', state: '', zip: '', notes: '',
  };
  const [form, setForm] = useState(emptyForm);

  function openEdit(contact) {
    setForm({
      id: contact.id,
      client_id: contact.client_id,
      first_name: contact.first_name,
      last_name: contact.last_name,
      email: contact.email || '',
      phone: contact.phone || '',
      mobile: contact.mobile || '',
      title: contact.title || '',
      is_primary: contact.is_primary,
      address: contact.address || '',
      city: contact.city || '',
      state: contact.state || '',
      zip: contact.zip || '',
      notes: contact.notes || '',
    });
    setEditContact(contact.id);
  }

  async function handleSave(e) {
    e.preventDefault();
    try {
      const payload = { ...form };
      Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });
      payload.is_primary = form.is_primary;
      payload.client_id = form.client_id;

      if (editContact) {
        await updateContact.mutateAsync(payload);
        setEditContact(null);
      } else {
        await createContact.mutateAsync(payload);
        setShowAdd(false);
      }
      setForm(emptyForm);
      setToast({ type: 'success', message: editContact ? 'Contact updated' : 'Contact created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  const items = data?.items || [];
  const clientList = clients?.items || [];

  const columns = [
    { key: 'name', label: 'Name', render: (row) => `${row.first_name} ${row.last_name}` },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'title', label: 'Title', render: (row) => row.title || '—' },
    { key: 'email', label: 'Email', render: (row) => row.email || '—' },
    { key: 'phone', label: 'Phone', render: (row) => row.phone || '—' },
    { key: 'primary', label: 'Primary', render: (row) => row.is_primary ? 'Yes' : '' },
    { key: 'actions', label: '', render: (row) => (
      <div style={{ display: 'flex', gap: '4px' }}>
        <button className="btn btn--small btn--outline" onClick={() => openEdit(row)}>Edit</button>
        <button className="btn btn--small btn--danger" onClick={() => deleteContact.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Deleted' }))}>Delete</button>
      </div>
    )},
  ];

  const isEditing = showAdd || editContact;

  return (
    <div>
      <div className="page-header">
        <h1>Contacts</h1>
        <button className="btn btn--primary" onClick={() => { setForm(emptyForm); setShowAdd(true); }}>+ Add Contact</button>
      </div>

      <div style={{ display: 'flex', gap: '12px', marginBottom: '16px' }}>
        <input
          type="text" placeholder="Search name or email..."
          value={filters.search}
          onChange={e => setFilters(f => ({ ...f, search: e.target.value }))}
          style={{ width: '250px' }}
        />
        <select value={filters.client_id} onChange={e => setFilters(f => ({ ...f, client_id: e.target.value }))}>
          <option value="">All Clients</option>
          {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
        </select>
      </div>

      <DataTable columns={columns} rows={items} emptyMessage="No contacts found" />

      <Modal isOpen={isEditing} title={editContact ? 'Edit Contact' : 'Add Contact'} onClose={() => { setShowAdd(false); setEditContact(null); }}>
          <form onSubmit={handleSave}>
            <FormField label="Client" required>
              <select value={form.client_id} onChange={e => setForm(f => ({ ...f, client_id: e.target.value }))} required disabled={!!editContact}>
                <option value="">Select...</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <FormField label="First Name" required>
                <input value={form.first_name} onChange={e => setForm(f => ({ ...f, first_name: e.target.value }))} required />
              </FormField>
              <FormField label="Last Name" required>
                <input value={form.last_name} onChange={e => setForm(f => ({ ...f, last_name: e.target.value }))} required />
              </FormField>
              <FormField label="Email">
                <input type="email" value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} />
              </FormField>
              <FormField label="Title">
                <input value={form.title} onChange={e => setForm(f => ({ ...f, title: e.target.value }))} />
              </FormField>
              <FormField label="Phone">
                <input value={form.phone} onChange={e => setForm(f => ({ ...f, phone: e.target.value }))} />
              </FormField>
              <FormField label="Mobile">
                <input value={form.mobile} onChange={e => setForm(f => ({ ...f, mobile: e.target.value }))} />
              </FormField>
            </div>
            <h3 style={{ marginTop: '16px' }}>Address</h3>
            <FormField label="Street">
              <input value={form.address} onChange={e => setForm(f => ({ ...f, address: e.target.value }))} />
            </FormField>
            <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr 1fr', gap: '12px' }}>
              <FormField label="City">
                <input value={form.city} onChange={e => setForm(f => ({ ...f, city: e.target.value }))} />
              </FormField>
              <FormField label="State">
                <input value={form.state} onChange={e => setForm(f => ({ ...f, state: e.target.value }))} maxLength={2} />
              </FormField>
              <FormField label="ZIP">
                <input value={form.zip} onChange={e => setForm(f => ({ ...f, zip: e.target.value }))} maxLength={10} />
              </FormField>
            </div>
            <FormField label="Primary Contact">
              <input type="checkbox" checked={form.is_primary} onChange={e => setForm(f => ({ ...f, is_primary: e.target.checked }))} />
            </FormField>
            <FormField label="Notes">
              <textarea value={form.notes} onChange={e => setForm(f => ({ ...f, notes: e.target.value }))} rows={2} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => { setShowAdd(false); setEditContact(null); }}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createContact.isPending || updateContact.isPending}>Save</button>
            </div>
          </form>
      </Modal>

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
