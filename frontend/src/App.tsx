import {
  BookOpen,
  LayoutDashboard,
  LogOut,
  Menu,
  TableProperties,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { ResultsOverviewPage } from './pages/ResultsOverviewPage'
import './App.css'

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Results overview', icon: TableProperties, to: '/results' },
]

function App() {
  const [menuOpen, setMenuOpen] = useState(false)
  const closeMenu = () => setMenuOpen(false)

  function handleLogOff() {
    // No auth system yet (Phase 4/6) - return to the landing route for now.
    window.location.assign('/')
  }

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
            <span className="user-name">Student STU0001</span>
            <button className="logout-btn" type="button" onClick={handleLogOff}>
              <LogOut size={15} aria-hidden="true" />
              Log off
            </button>
          </div>
        </header>
        <nav className={menuOpen ? 'navbar navbar--open' : 'navbar'} id="primary-navigation" aria-label="Primary navigation">
          <div className="navigation">
            {navigation.map(({ label, icon: Icon, to }) => (
              <NavLink className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'} key={label} to={to} end={to === '/'}>
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
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
