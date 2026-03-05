export function formatCurrency(amount) {
  if (amount == null) return '--';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
  }).format(amount);
}

export function formatDate(dateStr) {
  if (!dateStr) return '--';
  return new Date(dateStr).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

export function formatEntityType(type) {
  const map = {
    SOLE_PROP: 'Sole Proprietor',
    S_CORP: 'S-Corp',
    C_CORP: 'C-Corp',
    PARTNERSHIP_LLC: 'Partnership / LLC',
  };
  return map[type] || type;
}

export function formatStatus(status) {
  if (!status) return '';
  return status.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}
