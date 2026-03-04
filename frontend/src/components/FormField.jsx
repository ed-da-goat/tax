export function FormField({ label, error, children }) {
  return (
    <div className="form-field">
      {label && <label className="form-label">{label}</label>}
      {children}
      {error && <span className="form-error">{error}</span>}
    </div>
  );
}

export function SelectField({ label, name, value, onChange, options, error, placeholder }) {
  return (
    <FormField label={label} error={error}>
      <select
        name={name}
        value={value}
        onChange={onChange}
        className="form-input form-select"
      >
        {placeholder && <option value="">{placeholder}</option>}
        {options.map((opt) =>
          opt.group ? (
            <optgroup key={opt.group} label={opt.group}>
              {opt.items.map((item) => (
                <option key={item.value} value={item.value}>
                  {item.label}
                </option>
              ))}
            </optgroup>
          ) : (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          )
        )}
      </select>
    </FormField>
  );
}
