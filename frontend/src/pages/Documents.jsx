import { useState, useEffect, useCallback } from 'react';
import useApi from '../hooks/useApi';
import useAuth from '../hooks/useAuth';
import ClientSelector from '../components/ClientSelector';
import DataTable from '../components/DataTable';
import Modal from '../components/Modal';
import ConfirmDialog from '../components/ConfirmDialog';
import { FormField } from '../components/FormField';
import { formatDate } from '../utils/format';

export default function Documents() {
  const api = useApi();
  const { isCpaOwner } = useAuth();
  const [clientId, setClientId] = useState('');
  const [documents, setDocuments] = useState([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(0);
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const [file, setFile] = useState(null);
  const [description, setDescription] = useState('');
  const [tags, setTags] = useState('');
  const [confirm, setConfirm] = useState(null);

  const fetchDocuments = useCallback(async () => {
    if (!clientId) return;
    setLoading(true);
    try {
      const params = { skip: page * 25, limit: 25 };
      let url = `/api/v1/clients/${clientId}/documents`;
      if (search.trim()) {
        url = `/api/v1/clients/${clientId}/documents/search`;
        params.q = search.trim();
      }
      const res = await api.get(url, { params });
      setDocuments(res.data.items || []);
      setTotal(res.data.total || 0);
    } catch { /* ignore */ }
    setLoading(false);
  }, [clientId, page, search, api]);

  useEffect(() => { fetchDocuments(); }, [fetchDocuments]);

  const handleUpload = async () => {
    if (!file) return;
    setError('');
    try {
      const formData = new FormData();
      formData.append('file', file);
      if (description) formData.append('description', description);
      if (tags) formData.append('tags', tags);
      await api.post(`/api/v1/clients/${clientId}/documents`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setShowUpload(false);
      setFile(null);
      setDescription('');
      setTags('');
      fetchDocuments();
    } catch (e) {
      setError(e.response?.data?.detail || 'Upload failed');
    }
  };

  const handleDownload = async (doc) => {
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/documents/${doc.id}/download`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data]));
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', doc.file_name);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      setError(e.response?.data?.detail || 'Download failed');
    }
  };

  const handleView = async (doc) => {
    try {
      const res = await api.get(`/api/v1/clients/${clientId}/documents/${doc.id}/view`, { responseType: 'blob' });
      const url = window.URL.createObjectURL(new Blob([res.data], { type: doc.file_type || 'application/pdf' }));
      window.open(url, '_blank');
    } catch (e) {
      if (e.response?.data instanceof Blob) {
        const text = await e.response.data.text();
        try { setError(JSON.parse(text).detail); } catch { setError(text || 'View failed'); }
      } else {
        setError(e.response?.data?.detail || 'View failed');
      }
    }
  };

  const handleDelete = async (docId) => {
    try {
      await api.delete(`/api/v1/clients/${clientId}/documents/${docId}`);
      fetchDocuments();
    } catch (e) {
      setError(e.response?.data?.detail || 'Delete failed');
    }
    setConfirm(null);
  };

  function formatFileSize(bytes) {
    if (!bytes) return '--';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  const columns = [
    { key: 'file_name', label: 'File Name' },
    { key: 'file_type', label: 'Type', render: (v) => v || '--' },
    { key: 'file_size_bytes', label: 'Size', render: (v) => formatFileSize(v) },
    { key: 'description', label: 'Description', render: (v) => v || '--' },
    { key: 'tags', label: 'Tags', render: (v) => (v || []).join(', ') || '--' },
    { key: 'created_at', label: 'Uploaded', render: (v) => formatDate(v) },
    {
      key: 'id', label: 'Actions', render: (v, row) => (
        <div style={{ display: 'flex', gap: 4 }}>
          <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); handleView(row); }}>View</button>
          <button className="btn btn--small btn--outline" onClick={(e) => { e.stopPropagation(); handleDownload(row); }}>Download</button>
          {isCpaOwner() && (
            <button className="btn btn--small btn--danger" onClick={(e) => { e.stopPropagation(); setConfirm({ id: v, name: row.file_name }); }}>Delete</button>
          )}
        </div>
      ),
    },
  ];

  return (
    <div className="page">
      <div className="page-header">
        <h1 className="page-title">Documents</h1>
        <button className="btn btn--primary" onClick={() => setShowUpload(true)} disabled={!clientId}>Upload Document</button>
      </div>

      <div style={{ display: 'flex', gap: 12, alignItems: 'center', marginBottom: 16 }}>
        <ClientSelector value={clientId} onSelect={(id) => { setClientId(id); setPage(0); }} />
        <input className="form-input search-input" style={{ marginBottom: 0 }} placeholder="Search documents..." value={search} onChange={(e) => setSearch(e.target.value)} />
      </div>

      {error && <div className="alert alert--error">{error}</div>}

      <DataTable columns={columns} data={documents} total={total} page={page} onPageChange={setPage} loading={loading} emptyMessage="No documents found." />

      {/* Upload Modal */}
      <Modal isOpen={showUpload} onClose={() => setShowUpload(false)} title="Upload Document" size="md">
        <FormField label="File">
          <input className="form-input" type="file" onChange={(e) => setFile(e.target.files[0] || null)} />
        </FormField>
        <FormField label="Description (optional)">
          <input className="form-input" value={description} onChange={(e) => setDescription(e.target.value)} />
        </FormField>
        <FormField label="Tags (comma-separated, optional)">
          <input className="form-input" value={tags} onChange={(e) => setTags(e.target.value)} placeholder="receipt, expense, 2024" />
        </FormField>
        <div className="form-actions">
          <button className="btn btn--outline" onClick={() => setShowUpload(false)}>Cancel</button>
          <button className="btn btn--primary" onClick={handleUpload} disabled={!file}>Upload</button>
        </div>
      </Modal>

      <ConfirmDialog
        isOpen={!!confirm}
        title="Delete Document"
        message={`Delete "${confirm?.name}"? This is a soft delete.`}
        confirmLabel="Delete"
        onConfirm={() => handleDelete(confirm.id)}
        onCancel={() => setConfirm(null)}
      />
    </div>
  );
}
