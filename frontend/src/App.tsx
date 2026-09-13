import {
  BookOpen,
  LayoutDashboard,
  LogOut,
  Menu,
  Sparkles,
  TableProperties,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { ResultsOverviewPage } from './pages/ResultsOverviewPage'
import { StudyPlanPage } from './pages/StudyPlanPage'
import { StudentPicker } from './StudentPicker'
import { StudentProvider } from './studentContext'
import './App.css'

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Results overview', icon: TableProperties, to: '/results' },
  { label: 'Study plan', icon: Sparkles, to: '/study-plan' },
]

function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="app-shell">
      <div className="app-chrome">
        <header className="topbar">
          <NavLink className="brand" to="/" aria-label="Learning Journey Assistant dashboard" onClick={closeMenu}>
            <span className="brand-mark"><BookOpen size={17} aria-hidden="true" /></span>
            <span className="brand-name">Learning Journey Assistant</span>
          </NavLink>
          <button
            className="menu-toggle"
            type="button"
            aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
            aria-expanded={menuOpen}
            aria-controls="primary-navigation"
            onClick={() => setMenuOpen((open) => !open)}
          >
            {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
          </button>
          <div className="topbar-user">
            <StudentPicker />
            {/* Real sign-out: clears the Flask session server-side. */}
            <a className="logout-btn" href="/logout">
              <LogOut size={15} aria-hidden="true" />
              Log off
            </a>
          </div>
        </header>
        <nav className={menuOpen ? 'navbar navbar--open' : 'navbar'} id="primary-navigation" aria-label="Primary navigation">
          <div className="navigation">
            {navigation.map(({ label, icon: Icon, to }) => (
              <NavLink className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'} key={label} to={to} end={to === '/'} onClick={closeMenu}>
                <Icon size={16} aria-hidden="true" />
                {label}
              </NavLink>
            ))}
          </div>
        </nav>
      </div>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/results" element={<ResultsOverviewPage />} />
        <Route path="/study-plan" element={<StudyPlanPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

function App() {
  return (
    <StudentProvider>
      <AppShell />
    </StudentProvider>
  )
}

export default App
