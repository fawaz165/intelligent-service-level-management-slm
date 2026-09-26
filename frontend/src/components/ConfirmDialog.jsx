/**
 * ConfirmDialog — modal for destructive operation confirmation.
 */
export default function ConfirmDialog({ message, onConfirm, onCancel }) {
  return (
    <div className="confirm-overlay" onClick={onCancel}>
      <div className="confirm-dialog" onClick={e => e.stopPropagation()}>
        <div className="confirm-icon">⚠️</div>
        <div className="confirm-title">Confirm Action</div>
        <div className="confirm-message">{message}</div>
        <div className="confirm-actions">
          <button className="btn-confirm secondary" onClick={onCancel}>
            Cancel
          </button>
          <button className="btn-confirm danger" onClick={onConfirm}>
            Confirm Delete
          </button>
        </div>
      </div>
    </div>
  );
}
