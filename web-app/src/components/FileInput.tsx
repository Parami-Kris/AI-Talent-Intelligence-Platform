interface FileInputProps {
  id: string
  accept?: string
  multiple?: boolean
  disabled?: boolean
  value: File[]
  onChange: (files: File[]) => void
  placeholder?: string
}

export function FileInput({
  id,
  accept,
  multiple,
  disabled,
  value,
  onChange,
  placeholder = 'No file chosen',
}: FileInputProps) {
  return (
    <div>
      <div className="mt-1 flex items-center gap-3">
        <label
          htmlFor={id}
          className={`inline-flex shrink-0 cursor-pointer items-center rounded-md border border-gray-300 bg-white px-3 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200 dark:hover:bg-gray-700 ${
            disabled ? 'pointer-events-none opacity-50' : ''
          }`}
        >
          Browse…
        </label>
        <input
          id={id}
          type="file"
          accept={accept}
          multiple={multiple}
          disabled={disabled}
          onChange={(event) => onChange(Array.from(event.target.files ?? []))}
          className="hidden"
        />
        <span className="min-w-0 flex-1 truncate text-sm text-gray-600 dark:text-gray-400">
          {value.length === 0
            ? placeholder
            : value.length === 1
              ? value[0].name
              : `${value.length} files selected`}
        </span>
      </div>
      {value.length > 1 && (
        <ul className="mt-1 space-y-0.5 pl-1 text-xs text-gray-500 dark:text-gray-400">
          {value.map((file) => (
            <li key={file.name} className="truncate">
              {file.name}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
