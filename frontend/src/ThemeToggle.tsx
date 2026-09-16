import { useState } from 'react'
import { Moon, Sun } from 'lucide-react'

const KEY = 'lja-theme'

function current(): 'light' | 'dark' {
  const set = document.documentElement.getAttribute('data-theme')
  if (set === 'dark' || set === 'light') return set
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

/**
 * Light/dark switch. With no choice saved the app follows the system
 * setting (index.html applies a saved choice before React paints, so there
 * is no flash). The choice lives in this browser only - it is a viewing
 * preference, not student data.
 */
export function ThemeToggle() {
  const [theme, setTheme] = useState<'light' | 'dark'>(current)

  function toggle() {
    const next = theme === 'dark' ? 'light' : 'dark'
    document.documentElement.setAttribute('data-theme', next)
    try { localStorage.setItem(KEY, next) } catch { /* private mode: still applies for this page view */ }
    setTheme(next)
  }

  return (
    <button
      className="theme-toggle"
      type="button"
      onClick={toggle}
      aria-pressed={theme === 'dark'}
      aria-label={theme === 'dark' ? 'Switch to light theme' : 'Switch to dark theme'}
      title={theme === 'dark' ? 'Light theme' : 'Dark theme'}
    >
      {theme === 'dark' ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
    </button>
  )
}
