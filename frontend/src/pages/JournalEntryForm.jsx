import { useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useMutation } from '@tanstack/react-query';
import useApi from '../hooks/useApi';
import useToast from '../hooks/useToast';
import { FormField } from '../components/FormField';
import { useApiQuery } from '../hooks/useApiQuery';
import { formatCurrency } from '../utils/format';

const emptyLine = () => ({ account_id: '', description: '', debit: '', credit: '' });

export default function JournalEntryForm() {
  const { clientId } = useParams();
  const navigate = useNavigate();
  const api = useApi();
  const { addToast } = useToast();

  const { data: client } = useApiQuery(['client', clientId], `/api/v1/clients/${clientId}`);
  const { data: accountsData } = useApiQuery(['accounts', clientId], `/api/v1/clients/${clientId}/accounts`);

  const [form, setForm] = useState({
    entry_date: new Date().toISOString().split('T')[0],
    description: '',
    reference_number: '',
  });
  const [lines, setLines] = useState([emptyLine(), emptyLine()]);
  const [errors, setErrors] = useState({});

  const accounts = (accountsData?.items || []).filter((a) => a.is_active);

  // Group accounts by type for optgroup
  const accountGroups = {};
  accounts.forEach((a) => {
    if (!accountGroups[a.account_type]) accountGroups[a.account_type] = [];
    accountGroups[a.account_type].push(a);
  });

  const totalDebits = lines.reduce((sum, l) => sum + (parseFloat(l.debit) || 0), 0);
  const totalCredits = lines.reduce((sum, l) => sum + (parseFloat(l.credit) || 0), 0);
  const isBalanced = Math.abs(totalDebits - totalCredits) < 0.005 && totalDebits > 0;

  const createMutation = useMutation({
    mutationFn: async ({ submitAfter }) => {
      const body = {
        client_id: clientId,
        entry_date: form.entry_date,
        description: form.description || null,
        reference_number: form.reference_number || null,
        lines: lines
          .filter((l) => l.account_id)
          .map((l) => ({
            account_id: l.account_id,
            debit: l.debit ? String(l.debit) : '0.00',
            credit: l.credit ? String(l.credit) : '0.00',
            description: l.description || null,
          })),
      };
      const { data } = await api.post(`/api/v1/clients/${clientId}/journal-entries`, body);
      if (submitAfter) {
        await api.post(`/api/v1/clients/${clientId}/journal-entries/${data.id}/submit`);
      }
      return data;
    },
    onSuccess: (_, variables) => {
      addToast('success', variables.submitAfter ? 'Entry submitted for approval' : 'Entry saved as draft');
      navigate(`/clients/${clientId}?tab=journal`);
    },
    onError: (err) => addToast('error', err.response?.data?.detail || 'Failed to save entry'),
  });

  function updateLine(index, field, value) {
    const updated = [...lines];
    updated[index] = { ...updated[index], [field]: value };
    // If entering debit, clear credit and vice versa
    if (field === 'debit' && value) updated[index].credit = '';
    if (field === 'credit' && value) updated[index].debit = '';
    setLines(updated);
  }

  function addLine() {
    setLines([...lines, emptyLine()]);
  }

  function removeLine(index) {
    if (lines.length <= 2) return;
    setLines(lines.filter((_, i) => i !== index));
  }

  function validate() {
    const errs = {};
    if (!form.entry_date) errs.entry_date = 'Date is required';
    const validLines = lines.filter((l) => l.account_id);
    if (validLines.length < 2) errs.lines = 'At least 2 line items required';
    if (!isBalanced) errs.balance = 'Debits must equal credits';
    setErrors(errs);
    return Object.keys(errs).length === 0;
  }

  function handleSave(submitAfter) {
    if (!validate()) return;
    createMutation.mutate({ submitAfter });
  }

  return (
    <div className="page">
      <div className="breadcrumb">
        <Link to="/clients">Clients</Link>
        <span className="breadcrumb-sep">/</span>
        <Link to={`/clients/${clientId}`}>{client?.name || 'Client'}</Link>
        <span className="breadcrumb-sep">/</span>
        <span>New Journal Entry</span>
      </div>

      <h1 className="page-title">New Journal Entry</h1>

      {errors.balance && <div className="alert alert--error">{errors.balance}</div>}
      {errors.lines && <div className="alert alert--error">{errors.lines}</div>}

      <div className="card mb-24">
        <div className="form-row">
          <FormField label="Entry Date" error={errors.entry_date}>
            <input
              className="form-input"
              type="date"
              value={form.entry_date}
              onChange={(e) => setForm({ ...form, entry_date: e.target.value })}
            />
          </FormField>
          <FormField label="Description">
            <input
              className="form-input"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
              placeholder="Entry description"
            />
          </FormField>
          <FormField label="Reference #">
            <input
              className="form-input"
              value={form.reference_number}
              onChange={(e) => setForm({ ...form, reference_number: e.target.value })}
            />
          </FormField>
        </div>
      </div>

      <div className="section-header">
        <h2 className="section-title">Line Items</h2>
        <button className="btn btn--outline btn--small" onClick={addLine}>Add Line</button>
      </div>

      <table className="je-lines-table">
        <thead>
          <tr>
            <th style={{ width: '35%' }}>Account</th>
            <th style={{ width: '25%' }}>Description</th>
            <th style={{ width: '15%', textAlign: 'right' }}>Debit</th>
            <th style={{ width: '15%', textAlign: 'right' }}>Credit</th>
            <th style={{ width: '10%' }}></th>
          </tr>
        </thead>
        <tbody>
          {lines.map((line, i) => (
            <tr key={i}>
              <td>
                <select
                  className="form-input form-select"
                  value={line.account_id}
                  onChange={(e) => updateLine(i, 'account_id', e.target.value)}
                >
                  <option value="">Select account...</option>
                  {Object.entries(accountGroups).map(([type, accts]) => (
                    <optgroup key={type} label={type}>
                      {accts.map((a) => (
                        <option key={a.id} value={a.id}>
                          {a.account_number} - {a.account_name}
                        </option>
                      ))}
                    </optgroup>
                  ))}
                </select>
              </td>
              <td>
                <input
                  className="form-input"
                  value={line.description}
                  onChange={(e) => updateLine(i, 'description', e.target.value)}
                  placeholder="Line description"
                />
              </td>
              <td>
                <input
                  className="form-input text-right"
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.debit}
                  onChange={(e) => updateLine(i, 'debit', e.target.value)}
                  placeholder="0.00"
                />
              </td>
              <td>
                <input
                  className="form-input text-right"
                  type="number"
                  min="0"
                  step="0.01"
                  value={line.credit}
                  onChange={(e) => updateLine(i, 'credit', e.target.value)}
                  placeholder="0.00"
                />
              </td>
              <td>
                {lines.length > 2 && (
                  <button
                    className="btn btn--small btn--danger"
                    onClick={() => removeLine(i)}
                  >
                    X
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className={`je-totals ${!isBalanced && totalDebits > 0 ? 'je-totals--unbalanced' : ''}`}>
        <span>Debits: {formatCurrency(totalDebits)}</span>
        <span>Credits: {formatCurrency(totalCredits)}</span>
        {!isBalanced && totalDebits > 0 && (
          <span>Difference: {formatCurrency(Math.abs(totalDebits - totalCredits))}</span>
        )}
      </div>

      <div className="form-actions mt-16">
        <button className="btn btn--outline" onClick={() => navigate(`/clients/${clientId}?tab=journal`)}>
          Cancel
        </button>
        <button
          className="btn btn--outline"
          onClick={() => handleSave(false)}
          disabled={createMutation.isPending}
        >
          Save as Draft
        </button>
        <button
          className="btn btn--primary"
          onClick={() => handleSave(true)}
          disabled={createMutation.isPending}
        >
          Save & Submit for Approval
        </button>
      </div>
    </div>
  );
}
