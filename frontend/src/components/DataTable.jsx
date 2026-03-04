export default function DataTable({
  columns,
  data = [],
  total = 0,
  page = 0,
  pageSize = 25,
  onPageChange,
  loading = false,
  emptyMessage = 'No records found.',
  onRowClick,
  selectable = false,
  selectedIds = [],
  onSelectChange,
}) {
  const start = page * pageSize + 1;
  const end = Math.min((page + 1) * pageSize, total);
  const totalPages = Math.ceil(total / pageSize);

  return (
    <div className="table-wrapper">
      <table className={`table ${loading ? 'table--loading' : ''}`}>
        <thead>
          <tr>
            {selectable && (
              <th style={{ width: 36 }}>
                <input
                  type="checkbox"
                  checked={data.length > 0 && data.every((r) => selectedIds.includes(r.id))}
                  onChange={(e) => {
                    if (e.target.checked) {
                      onSelectChange(data.map((r) => r.id));
                    } else {
                      onSelectChange([]);
                    }
                  }}
                />
              </th>
            )}
            {columns.map((col) => (
              <th key={col.key} style={col.style}>{col.label}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {data.length === 0 && !loading ? (
            <tr>
              <td colSpan={columns.length + (selectable ? 1 : 0)}>
                <div className="empty-state">{emptyMessage}</div>
              </td>
            </tr>
          ) : (
            data.map((row) => (
              <tr
                key={row.id}
                onClick={() => onRowClick && onRowClick(row)}
                style={onRowClick ? { cursor: 'pointer' } : undefined}
              >
                {selectable && (
                  <td onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      checked={selectedIds.includes(row.id)}
                      onChange={(e) => {
                        if (e.target.checked) {
                          onSelectChange([...selectedIds, row.id]);
                        } else {
                          onSelectChange(selectedIds.filter((id) => id !== row.id));
                        }
                      }}
                    />
                  </td>
                )}
                {columns.map((col) => (
                  <td key={col.key}>
                    {col.render ? col.render(row[col.key], row) : row[col.key] ?? '--'}
                  </td>
                ))}
              </tr>
            ))
          )}
        </tbody>
      </table>

      {total > pageSize && onPageChange && (
        <div className="pagination">
          <span className="pagination-info">
            {total > 0 ? `${start}-${end} of ${total}` : '0 results'}
          </span>
          <div className="pagination-buttons">
            <button
              className="btn btn--small btn--outline"
              disabled={page === 0}
              onClick={() => onPageChange(page - 1)}
            >
              Prev
            </button>
            <span className="pagination-page">
              {page + 1} / {totalPages}
            </span>
            <button
              className="btn btn--small btn--outline"
              disabled={page + 1 >= totalPages}
              onClick={() => onPageChange(page + 1)}
            >
              Next
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
