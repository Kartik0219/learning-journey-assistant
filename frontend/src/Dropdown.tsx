import { useEffect, useRef, useState, type ComponentType } from 'react'
import { Check, ChevronDown } from 'lucide-react'

interface DropdownOption {
  value: string
  label: string
}

interface DropdownProps {
  label: string
  value: string
  options: DropdownOption[]
  onChange: (value: string) => void
  icon?: ComponentType<{ size?: number; 'aria-hidden'?: boolean }>
  ariaLabel?: string
}

export function Dropdown({ label, value, options, onChange, icon: Icon, ariaLabel }: DropdownProps) {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const current = options.find((option) => option.value === value) ?? options[0]

  useEffect(() => {
    if (!open) return
    function onPointerDown(event: MouseEvent) {
      if (ref.current && !ref.current.contains(event.target as Node)) setOpen(false)
    }
    function onKeyDown(event: KeyboardEvent) {
      if (event.key === 'Escape') setOpen(false)
    }
    document.addEventListener('mousedown', onPointerDown)
    document.addEventListener('keydown', onKeyDown)
    return () => {
      document.removeEventListener('mousedown', onPointerDown)
      document.removeEventListener('keydown', onKeyDown)
    }
  }, [open])

  return (
    <div className="dropdown" ref={ref}>
      <span className="dropdown__label">{label}</span>
      <div className="dropdown__field">
        <button
          type="button"
          className="dropdown__button"
          aria-haspopup="listbox"
          aria-expanded={open}
          aria-label={ariaLabel ?? label}
          onClick={() => setOpen((value) => !value)}
        >
          {Icon && <Icon size={14} aria-hidden={true} />}
          <span className="dropdown__current">{current?.label}</span>
          <ChevronDown size={14} aria-hidden={true} className={open ? 'dropdown__chev open' : 'dropdown__chev'} />
        </button>
        {open && (
          <ul className="dropdown__menu" role="listbox" aria-label={label}>
            {options.map((option) => (
              <li key={option.value} role="option" aria-selected={option.value === value}>
                <button
                  type="button"
                  className={option.value === value ? 'dropdown__opt selected' : 'dropdown__opt'}
                  onClick={() => {
                    onChange(option.value)
                    setOpen(false)
                  }}
                >
                  <Check size={14} aria-hidden={true} className="dropdown__check" />
                  {option.label}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
