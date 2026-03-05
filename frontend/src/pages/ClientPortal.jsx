import { useState } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Tabs from '../components/Tabs';
import Toast from '../components/Toast';
import { formatDate } from '../utils/format';

const Q_STATUS_COLORS = {
  DRAFT: '#6B7280', SENT: '#3B82F6', IN_PROGRESS: '#F59E0B',
  SUBMITTED: '#10B981', REVIEWED: '#8B5CF6',
};

const SIG_STATUS_COLORS = {
  PENDING: '#F59E0B', SIGNED: '#10B981', DECLINED: '#EF4444', EXPIRED: '#9CA3AF',
};

export default function ClientPortal() {
  const [toast, setToast] = useState(null);
  const [activeTab, setActiveTab] = useState('portal-users');
  const [showAddUser, setShowAddUser] = useState(false);
  const [showAddQ, setShowAddQ] = useState(false);
  const [showAddSig, setShowAddSig] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const [msgClient, setMsgClient] = useState('');

  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const { data: portalUsers } = useApiQuery(['portal-users'], '/api/v1/portal-users');
  const { data: questionnaires } = useApiQuery(['questionnaires'], '/api/v1/questionnaires');
  const { data: signatures } = useApiQuery(['signatures'], '/api/v1/signatures');

  const createUser = useApiMutation('post', '/api/v1/portal-users', { invalidate: [['portal-users']] });
  const createQ = useApiMutation('post', '/api/v1/questionnaires', { invalidate: [['questionnaires']] });
  const sendQ = useApiMutation('post', (body) => `/api/v1/questionnaires/${body.id}/send`, { invalidate: [['questionnaires']] });
  const createSig = useApiMutation('post', '/api/v1/signatures', { invalidate: [['signatures']] });
  const sendMsg = useApiMutation('post', '/api/v1/messages', { invalidate: [['messages']] });

  const clientList = clients?.items || [];

  // --- Portal User Form ---
  const [userForm, setUserForm] = useState({ client_id: '', email: '', full_name: '', password: '' });
  async function handleAddUser(e) {
    e.preventDefault();
    try {
      await createUser.mutateAsync(userForm);
      setShowAddUser(false);
      setUserForm({ client_id: '', email: '', full_name: '', password: '' });
      setToast({ type: 'success', message: 'Portal user created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // --- Questionnaire Form ---
  const [qForm, setQForm] = useState({ client_id: '', title: '', questionnaire_type: 'Tax Organizer', tax_year: '2026', description: '', questions: [] });
  const [newQuestion, setNewQuestion] = useState({ question_text: '', question_type: 'TEXT', is_required: false });

  function addQuestion() {
    if (!newQuestion.question_text) return;
    setQForm(f => ({
      ...f,
      questions: [...f.questions, { ...newQuestion, sort_order: f.questions.length }],
    }));
    setNewQuestion({ question_text: '', question_type: 'TEXT', is_required: false });
  }

  async function handleAddQ(e) {
    e.preventDefault();
    try {
      await createQ.mutateAsync({ ...qForm, tax_year: parseInt(qForm.tax_year) || null });
      setShowAddQ(false);
      setQForm({ client_id: '', title: '', questionnaire_type: 'Tax Organizer', tax_year: '2026', description: '', questions: [] });
      setToast({ type: 'success', message: 'Questionnaire created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // --- Signature Request Form ---
  const [sigForm, setSigForm] = useState({ client_id: '', signer_name: '', signer_email: '', expires_in_days: 30 });
  async function handleAddSig(e) {
    e.preventDefault();
    try {
      await createSig.mutateAsync({ ...sigForm, expires_in_days: parseInt(sigForm.expires_in_days) });
      setShowAddSig(false);
      setSigForm({ client_id: '', signer_name: '', signer_email: '', expires_in_days: 30 });
      setToast({ type: 'success', message: 'Signature request created' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // --- Message Form ---
  const [msgForm, setMsgForm] = useState({ client_id: '', subject: '', body: '' });
  async function handleSendMsg(e) {
    e.preventDefault();
    try {
      await sendMsg.mutateAsync(msgForm);
      setShowMessage(false);
      setMsgForm({ client_id: '', subject: '', body: '' });
      setToast({ type: 'success', message: 'Message sent' });
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // --- Tables ---
  const userColumns = [
    { key: 'full_name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'is_active', label: 'Active', render: (row) => row.is_active ? 'Yes' : 'No' },
    { key: 'last_login', label: 'Last Login', render: (row) => row.last_login_at ? formatDate(row.last_login_at) : 'Never' },
  ];

  const qColumns = [
    { key: 'title', label: 'Title' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'questionnaire_type', label: 'Type' },
    { key: 'tax_year', label: 'Year', render: (row) => row.tax_year || '—' },
    { key: 'questions', label: 'Questions', render: (row) => row.questions?.length || 0 },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: Q_STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
    { key: 'actions', label: '', render: (row) => (
      row.status === 'DRAFT' && <button className="btn btn--small btn--primary" onClick={() => sendQ.mutateAsync({ id: row.id }).then(() => setToast({ type: 'success', message: 'Sent' }))}>Send</button>
    )},
  ];

  const sigColumns = [
    { key: 'signer_name', label: 'Signer' },
    { key: 'signer_email', label: 'Email' },
    { key: 'client', label: 'Client', render: (row) => clientList.find(c => c.id === row.client_id)?.name || '—' },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: SIG_STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
    { key: 'expires_at', label: 'Expires', render: (row) => row.expires_at ? formatDate(row.expires_at) : '—' },
    { key: 'signed_at', label: 'Signed', render: (row) => row.signed_at ? formatDate(row.signed_at) : '—' },
  ];

  const tabs = [
    { id: 'portal-users', label: 'Portal Users' },
    { id: 'messages', label: 'Messages' },
    { id: 'questionnaires', label: 'Questionnaires' },
    { id: 'signatures', label: 'E-Signatures' },
  ];

  return (
    <div>
      <div className="page-header">
        <h1>Client Portal</h1>
        <div style={{ display: 'flex', gap: '8px' }}>
          {activeTab === 'portal-users' && <button className="btn btn--primary" onClick={() => setShowAddUser(true)}>+ Add Portal User</button>}
          {activeTab === 'messages' && <button className="btn btn--primary" onClick={() => setShowMessage(true)}>+ New Message</button>}
          {activeTab === 'questionnaires' && <button className="btn btn--primary" onClick={() => setShowAddQ(true)}>+ New Questionnaire</button>}
          {activeTab === 'signatures' && <button className="btn btn--primary" onClick={() => setShowAddSig(true)}>+ Request Signature</button>}
        </div>
      </div>

      <Tabs tabs={tabs} active={activeTab} onChange={setActiveTab} />

      {activeTab === 'portal-users' && (
        <DataTable columns={userColumns} rows={portalUsers?.items || []} emptyMessage="No portal users" />
      )}
      {activeTab === 'messages' && (
        <div style={{ padding: '40px', textAlign: 'center', color: '#6B7280' }}>
          <p>Select a client and use the New Message button to send messages.</p>
          <p style={{ fontSize: '14px', marginTop: '8px' }}>Messages are organized by client thread.</p>
        </div>
      )}
      {activeTab === 'questionnaires' && (
        <DataTable columns={qColumns} rows={questionnaires?.items || []} emptyMessage="No questionnaires" />
      )}
      {activeTab === 'signatures' && (
        <DataTable columns={sigColumns} rows={signatures?.items || []} emptyMessage="No signature requests" />
      )}

      {/* Add Portal User Modal */}
      {showAddUser && (
        <Modal title="Add Portal User" onClose={() => setShowAddUser(false)}>
          <form onSubmit={handleAddUser}>
            <FormField label="Client" required>
              <select value={userForm.client_id} onChange={e => setUserForm(f => ({ ...f, client_id: e.target.value }))} required>
                <option value="">Select...</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <FormField label="Full Name" required>
              <input value={userForm.full_name} onChange={e => setUserForm(f => ({ ...f, full_name: e.target.value }))} required />
            </FormField>
            <FormField label="Email" required>
              <input type="email" value={userForm.email} onChange={e => setUserForm(f => ({ ...f, email: e.target.value }))} required />
            </FormField>
            <FormField label="Password" required>
              <input type="password" value={userForm.password} onChange={e => setUserForm(f => ({ ...f, password: e.target.value }))} required minLength={8} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAddUser(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createUser.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Send Message Modal */}
      {showMessage && (
        <Modal title="New Message" onClose={() => setShowMessage(false)}>
          <form onSubmit={handleSendMsg}>
            <FormField label="Client" required>
              <select value={msgForm.client_id} onChange={e => setMsgForm(f => ({ ...f, client_id: e.target.value }))} required>
                <option value="">Select...</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <FormField label="Subject">
              <input value={msgForm.subject} onChange={e => setMsgForm(f => ({ ...f, subject: e.target.value }))} />
            </FormField>
            <FormField label="Message" required>
              <textarea value={msgForm.body} onChange={e => setMsgForm(f => ({ ...f, body: e.target.value }))} rows={4} required />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowMessage(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={sendMsg.isPending}>Send</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Add Questionnaire Modal */}
      {showAddQ && (
        <Modal title="New Questionnaire" onClose={() => setShowAddQ(false)} wide>
          <form onSubmit={handleAddQ}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '12px' }}>
              <FormField label="Client" required>
                <select value={qForm.client_id} onChange={e => setQForm(f => ({ ...f, client_id: e.target.value }))} required>
                  <option value="">Select...</option>
                  {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
                </select>
              </FormField>
              <FormField label="Type">
                <select value={qForm.questionnaire_type} onChange={e => setQForm(f => ({ ...f, questionnaire_type: e.target.value }))}>
                  <option value="Tax Organizer">Tax Organizer</option>
                  <option value="New Client Intake">New Client Intake</option>
                  <option value="Year-End Review">Year-End Review</option>
                  <option value="Custom">Custom</option>
                </select>
              </FormField>
              <FormField label="Title" required>
                <input value={qForm.title} onChange={e => setQForm(f => ({ ...f, title: e.target.value }))} required />
              </FormField>
              <FormField label="Tax Year">
                <input type="number" value={qForm.tax_year} onChange={e => setQForm(f => ({ ...f, tax_year: e.target.value }))} />
              </FormField>
            </div>
            <FormField label="Description">
              <textarea value={qForm.description} onChange={e => setQForm(f => ({ ...f, description: e.target.value }))} rows={2} />
            </FormField>

            <h3 style={{ marginTop: '16px' }}>Questions ({qForm.questions.length})</h3>
            {qForm.questions.map((q, i) => (
              <div key={i} style={{ display: 'flex', gap: '8px', alignItems: 'center', padding: '6px 0', borderBottom: '1px solid #e5e7eb' }}>
                <span style={{ flex: 1 }}>{q.question_text}</span>
                <span className="badge" style={{ backgroundColor: '#6B7280' }}>{q.question_type}</span>
                {q.is_required && <span className="badge" style={{ backgroundColor: '#EF4444' }}>Required</span>}
                <button type="button" className="btn btn--small btn--danger" onClick={() => setQForm(f => ({ ...f, questions: f.questions.filter((_, j) => j !== i) }))}>X</button>
              </div>
            ))}
            <div style={{ display: 'grid', gridTemplateColumns: '3fr 1fr auto auto', gap: '8px', marginTop: '8px' }}>
              <input placeholder="Question text..." value={newQuestion.question_text} onChange={e => setNewQuestion(f => ({ ...f, question_text: e.target.value }))} />
              <select value={newQuestion.question_type} onChange={e => setNewQuestion(f => ({ ...f, question_type: e.target.value }))}>
                <option value="TEXT">Text</option>
                <option value="TEXTAREA">Long Text</option>
                <option value="NUMBER">Number</option>
                <option value="DATE">Date</option>
                <option value="YES_NO">Yes/No</option>
                <option value="FILE_UPLOAD">File Upload</option>
              </select>
              <label style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                <input type="checkbox" checked={newQuestion.is_required} onChange={e => setNewQuestion(f => ({ ...f, is_required: e.target.checked }))} /> Req
              </label>
              <button type="button" className="btn btn--small btn--outline" onClick={addQuestion}>+ Add</button>
            </div>

            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAddQ(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createQ.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {/* Signature Request Modal */}
      {showAddSig && (
        <Modal title="Request E-Signature" onClose={() => setShowAddSig(false)}>
          <form onSubmit={handleAddSig}>
            <FormField label="Client" required>
              <select value={sigForm.client_id} onChange={e => setSigForm(f => ({ ...f, client_id: e.target.value }))} required>
                <option value="">Select...</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </FormField>
            <FormField label="Signer Name" required>
              <input value={sigForm.signer_name} onChange={e => setSigForm(f => ({ ...f, signer_name: e.target.value }))} required />
            </FormField>
            <FormField label="Signer Email" required>
              <input type="email" value={sigForm.signer_email} onChange={e => setSigForm(f => ({ ...f, signer_email: e.target.value }))} required />
            </FormField>
            <FormField label="Expires In (days)">
              <input type="number" min="1" max="365" value={sigForm.expires_in_days} onChange={e => setSigForm(f => ({ ...f, expires_in_days: e.target.value }))} />
            </FormField>
            <div className="modal-actions">
              <button type="button" className="btn btn--outline" onClick={() => setShowAddSig(false)}>Cancel</button>
              <button type="submit" className="btn btn--primary" disabled={createSig.isPending}>Create</button>
            </div>
          </form>
        </Modal>
      )}

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
