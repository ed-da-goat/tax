import { useState, useEffect, useRef } from 'react';
import { useApiQuery, useApiMutation } from '../hooks/useApiQuery';
import useAuth from '../hooks/useAuth';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import { FormField } from '../components/FormField';
import Tabs from '../components/Tabs';
import Toast from '../components/Toast';
import { formatDate } from '../utils/format';

const Q_STATUS_COLORS = {
  DRAFT: '#6B7280', SENT: '#3d6d8e', IN_PROGRESS: '#F59E0B',
  SUBMITTED: '#10B981', REVIEWED: '#8B5CF6',
};

const SIG_STATUS_COLORS = {
  PENDING: '#F59E0B', SIGNED: '#10B981', DECLINED: '#EF4444', EXPIRED: '#9CA3AF',
};

export default function ClientPortal() {
  const { user } = useAuth();
  const [toast, setToast] = useState(null);
  const [activeTab, setActiveTab] = useState('portal-users');
  const [showAddUser, setShowAddUser] = useState(false);
  const [showAddQ, setShowAddQ] = useState(false);
  const [showAddSig, setShowAddSig] = useState(false);
  const [showMessage, setShowMessage] = useState(false);
  const [msgClientFilter, setMsgClientFilter] = useState('');
  const [selectedThread, setSelectedThread] = useState(null);
  const [replyText, setReplyText] = useState('');
  const messagesEndRef = useRef(null);

  const { data: clients } = useApiQuery(['clients'], '/api/v1/clients');
  const { data: portalUsers } = useApiQuery(['portal-users'], '/api/v1/portal-users');
  const { data: questionnaires } = useApiQuery(['questionnaires'], '/api/v1/questionnaires');
  const { data: signatures } = useApiQuery(['signatures'], '/api/v1/signatures');
  const { data: messages, refetch: refetchMessages } = useApiQuery(['messages'], '/api/v1/messages');

  const createUser = useApiMutation('post', '/api/v1/portal-users', { invalidate: [['portal-users']] });
  const createQ = useApiMutation('post', '/api/v1/questionnaires', { invalidate: [['questionnaires']] });
  const sendQ = useApiMutation('post', (body) => `/api/v1/questionnaires/${body.id}/send`, { invalidate: [['questionnaires']] });
  const createSig = useApiMutation('post', '/api/v1/signatures', { invalidate: [['signatures']] });
  const sendMsg = useApiMutation('post', '/api/v1/messages', { invalidate: [['messages']] });

  const clientList = clients?.items || [];
  const messageList = messages?.items || [];

  // Group messages by thread_id
  const threads = {};
  messageList.forEach(msg => {
    const tid = msg.thread_id || msg.id;
    if (!threads[tid]) {
      threads[tid] = { id: tid, subject: msg.subject || '(No subject)', client_id: msg.client_id, messages: [] };
    }
    threads[tid].messages.push(msg);
  });
  // Sort each thread's messages by created_at
  Object.values(threads).forEach(t => t.messages.sort((a, b) => new Date(a.created_at) - new Date(b.created_at)));

  let filteredThreads = Object.values(threads);
  if (msgClientFilter) {
    filteredThreads = filteredThreads.filter(t => t.client_id === msgClientFilter);
  }
  filteredThreads.sort((a, b) => {
    const aLast = a.messages[a.messages.length - 1]?.created_at || '';
    const bLast = b.messages[b.messages.length - 1]?.created_at || '';
    return new Date(bLast) - new Date(aLast);
  });

  // Scroll to bottom of thread when selected
  useEffect(() => {
    if (selectedThread && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [selectedThread, messageList.length]);

  function getClientName(cid) {
    return clientList.find(c => c.id === cid)?.name || 'Unknown';
  }

  function formatMessageTime(ts) {
    if (!ts) return '';
    const d = new Date(ts);
    const now = new Date();
    const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diffDays === 1) return 'Yesterday';
    if (diffDays < 7) return d.toLocaleDateString([], { weekday: 'short' });
    return formatDate(ts);
  }

  async function handleReply(e) {
    e.preventDefault();
    if (!replyText.trim() || !selectedThread) return;
    const thread = threads[selectedThread];
    try {
      await sendMsg.mutateAsync({
        client_id: thread.client_id,
        subject: thread.subject,
        body: replyText.trim(),
        thread_id: thread.id,
      });
      setReplyText('');
      refetchMessages();
    } catch (err) {
      setToast({ type: 'error', message: err.response?.data?.detail || 'Failed to send reply' });
    }
  }

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
      refetchMessages();
    } catch (err) { setToast({ type: 'error', message: err.response?.data?.detail || 'Failed' }); }
  }

  // --- Tables ---
  const userColumns = [
    { key: 'full_name', label: 'Name' },
    { key: 'email', label: 'Email' },
    { key: 'client', label: 'Client', render: (row) => getClientName(row.client_id) },
    { key: 'is_active', label: 'Active', render: (row) => row.is_active ? 'Yes' : 'No' },
    { key: 'last_login', label: 'Last Login', render: (row) => row.last_login_at ? formatDate(row.last_login_at) : 'Never' },
  ];

  const qColumns = [
    { key: 'title', label: 'Title' },
    { key: 'client', label: 'Client', render: (row) => getClientName(row.client_id) },
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
    { key: 'client', label: 'Client', render: (row) => getClientName(row.client_id) },
    { key: 'status', label: 'Status', render: (row) => (
      <span className="badge" style={{ backgroundColor: SIG_STATUS_COLORS[row.status] }}>{row.status}</span>
    )},
    { key: 'expires_at', label: 'Expires', render: (row) => row.expires_at ? formatDate(row.expires_at) : '—' },
    { key: 'signed_at', label: 'Signed', render: (row) => row.signed_at ? formatDate(row.signed_at) : '—' },
  ];

  const tabs = [
    { key: 'portal-users', label: 'Portal Users' },
    { key: 'messages', label: `Messages${messageList.length > 0 ? ` (${filteredThreads.length})` : ''}` },
    { key: 'questionnaires', label: 'Questionnaires' },
    { key: 'signatures', label: 'E-Signatures' },
  ];

  const selectedThreadData = selectedThread ? threads[selectedThread] : null;

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

      <Tabs tabs={tabs} activeTab={activeTab} onTabChange={setActiveTab} />

      {activeTab === 'portal-users' && (
        <DataTable columns={userColumns} rows={portalUsers?.items || []} emptyMessage="No portal users" />
      )}

      {activeTab === 'messages' && (
        <div style={{ display: 'flex', gap: '0', border: '1px solid #E5E7EB', borderRadius: '8px', minHeight: '500px', overflow: 'hidden' }}>
          {/* Thread list sidebar */}
          <div style={{ width: '320px', borderRight: '1px solid #E5E7EB', overflowY: 'auto', flexShrink: 0 }}>
            {/* Client filter */}
            <div style={{ padding: '12px', borderBottom: '1px solid #E5E7EB' }}>
              <select
                value={msgClientFilter}
                onChange={e => { setMsgClientFilter(e.target.value); setSelectedThread(null); }}
                style={{ width: '100%', padding: '6px 8px', borderRadius: '4px', border: '1px solid #D1D5DB', fontSize: '13px' }}
              >
                <option value="">All Clients</option>
                {clientList.map(c => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>

            {filteredThreads.length === 0 ? (
              <div style={{ padding: '40px 20px', textAlign: 'center', color: '#9CA3AF', fontSize: '13px' }}>
                No message threads
              </div>
            ) : (
              filteredThreads.map(thread => {
                const lastMsg = thread.messages[thread.messages.length - 1];
                const unread = thread.messages.some(m => !m.is_read && m.sender_type === 'CLIENT');
                const isSelected = selectedThread === thread.id;
                return (
                  <div
                    key={thread.id}
                    onClick={() => setSelectedThread(thread.id)}
                    style={{
                      padding: '12px 16px', cursor: 'pointer',
                      borderBottom: '1px solid #F3F4F6',
                      backgroundColor: isSelected ? '#EFF6FF' : unread ? '#FEF3C7' : 'white',
                      transition: 'background-color 0.15s',
                    }}
                    onMouseEnter={e => { if (!isSelected) e.currentTarget.style.backgroundColor = '#F9FAFB'; }}
                    onMouseLeave={e => { if (!isSelected) e.currentTarget.style.backgroundColor = unread ? '#FEF3C7' : 'white'; }}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '4px' }}>
                      <div style={{ fontWeight: unread ? 700 : 500, fontSize: '14px', color: '#111827' }}>
                        {thread.subject}
                      </div>
                      <span style={{ fontSize: '11px', color: '#9CA3AF', whiteSpace: 'nowrap', marginLeft: '8px' }}>
                        {formatMessageTime(lastMsg?.created_at)}
                      </span>
                    </div>
                    <div style={{ fontSize: '12px', color: '#6B7280', marginBottom: '2px' }}>
                      {getClientName(thread.client_id)}
                    </div>
                    <div style={{ fontSize: '13px', color: '#6B7280', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {lastMsg?.body?.substring(0, 80) || ''}
                    </div>
                  </div>
                );
              })
            )}
          </div>

          {/* Message thread view */}
          <div style={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
            {selectedThreadData ? (
              <>
                {/* Thread header */}
                <div style={{ padding: '16px', borderBottom: '1px solid #E5E7EB', backgroundColor: '#F9FAFB' }}>
                  <h3 style={{ margin: 0, fontSize: '16px', fontWeight: 600, color: '#111827' }}>
                    {selectedThreadData.subject}
                  </h3>
                  <div style={{ fontSize: '13px', color: '#6B7280', marginTop: '4px' }}>
                    {getClientName(selectedThreadData.client_id)} &middot; {selectedThreadData.messages.length} messages
                  </div>
                </div>

                {/* Messages */}
                <div style={{ flex: 1, overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  {selectedThreadData.messages.map(msg => {
                    const isStaff = msg.sender_type === 'STAFF';
                    return (
                      <div key={msg.id} style={{
                        display: 'flex', justifyContent: isStaff ? 'flex-end' : 'flex-start',
                      }}>
                        <div style={{
                          maxWidth: '70%', padding: '10px 14px', borderRadius: '12px',
                          backgroundColor: isStaff ? '#3d6d8e' : '#F3F4F6',
                          color: isStaff ? 'white' : '#111827',
                        }}>
                          <div style={{ fontSize: '11px', marginBottom: '4px', opacity: 0.7, fontWeight: 500 }}>
                            {isStaff ? (msg.sender_user_id === user?.id ? 'You' : 'Staff') : getClientName(msg.client_id)}
                          </div>
                          <div style={{ fontSize: '14px', lineHeight: '1.5', whiteSpace: 'pre-wrap' }}>
                            {msg.body}
                          </div>
                          <div style={{ fontSize: '11px', marginTop: '6px', opacity: 0.6, textAlign: 'right' }}>
                            {formatMessageTime(msg.created_at)}
                            {msg.is_read && isStaff && ' \u2713'}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                  <div ref={messagesEndRef} />
                </div>

                {/* Reply box */}
                <form onSubmit={handleReply} style={{
                  padding: '12px 16px', borderTop: '1px solid #E5E7EB',
                  display: 'flex', gap: '8px', backgroundColor: '#F9FAFB',
                }}>
                  <input
                    value={replyText}
                    onChange={e => setReplyText(e.target.value)}
                    placeholder="Type a reply..."
                    style={{
                      flex: 1, padding: '10px 14px', borderRadius: '20px',
                      border: '1px solid #D1D5DB', fontSize: '14px', outline: 'none',
                    }}
                    onFocus={e => e.target.style.borderColor = '#3d6d8e'}
                    onBlur={e => e.target.style.borderColor = '#D1D5DB'}
                  />
                  <button
                    type="submit"
                    className="btn btn--primary"
                    disabled={!replyText.trim() || sendMsg.isPending}
                    style={{ borderRadius: '20px', padding: '10px 20px' }}
                  >
                    {sendMsg.isPending ? 'Sending...' : 'Send'}
                  </button>
                </form>
              </>
            ) : (
              <div style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#9CA3AF' }}>
                <div style={{ textAlign: 'center' }}>
                  <div style={{ fontSize: '48px', marginBottom: '12px', opacity: 0.5 }}>{'\uD83D\uDCE8'}</div>
                  <p style={{ fontSize: '16px', margin: 0 }}>Select a conversation to view messages</p>
                  <p style={{ fontSize: '13px', marginTop: '4px' }}>Or start a new conversation with the button above</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {activeTab === 'questionnaires' && (
        <DataTable columns={qColumns} rows={questionnaires?.items || []} emptyMessage="No questionnaires" />
      )}
      {activeTab === 'signatures' && (
        <DataTable columns={sigColumns} rows={signatures?.items || []} emptyMessage="No signature requests" />
      )}

      {/* Add Portal User Modal */}
      <Modal isOpen={showAddUser} title="Add Portal User" onClose={() => setShowAddUser(false)}>
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

      {/* Send Message Modal */}
      <Modal isOpen={showMessage} title="New Message" onClose={() => setShowMessage(false)}>
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

      {/* Add Questionnaire Modal */}
      <Modal isOpen={showAddQ} title="New Questionnaire" onClose={() => setShowAddQ(false)} size="lg">
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

      {/* Signature Request Modal */}
      <Modal isOpen={showAddSig} title="Request E-Signature" onClose={() => setShowAddSig(false)}>
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

      {toast && <Toast {...toast} onClose={() => setToast(null)} />}
    </div>
  );
}
