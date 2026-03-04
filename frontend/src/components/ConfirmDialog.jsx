import Modal from './Modal';

export default function ConfirmDialog({
  isOpen,
  onConfirm,
  onCancel,
  title = 'Confirm',
  message,
  confirmLabel = 'Confirm',
  confirmVariant = 'danger',
}) {
  return (
    <Modal isOpen={isOpen} onClose={onCancel} title={title} size="sm">
      <p style={{ marginBottom: 20 }}>{message}</p>
      <div className="form-actions">
        <button className="btn btn--outline" onClick={onCancel}>Cancel</button>
        <button className={`btn btn--${confirmVariant}`} onClick={onConfirm}>
          {confirmLabel}
        </button>
      </div>
    </Modal>
  );
}
