const STATUS_CLASS = {
  DRAFT: 'badge--draft',
  PENDING_APPROVAL: 'badge--pending',
  POSTED: 'badge--posted',
  APPROVED: 'badge--approved',
  SENT: 'badge--sent',
  PAID: 'badge--paid',
  VOIDED: 'badge--void',
  VOID: 'badge--void',
  OVERDUE: 'badge--overdue',
  ACTIVE: 'badge--posted',
  ARCHIVED: 'badge--draft',
  FINALIZED: 'badge--approved',
  IN_PROGRESS: 'badge--pending',
  COMPLETED: 'badge--approved',
  RECEIVED: 'badge--paid',
  NEEDED: 'badge--pending',
  NOT_APPLICABLE: 'badge--draft',
};

export default function StatusBadge({ status }) {
  if (!status) return null;
  const cls = STATUS_CLASS[status] || 'badge--draft';
  const label = status.replace(/_/g, ' ');
  return <span className={`badge ${cls}`}>{label}</span>;
}
