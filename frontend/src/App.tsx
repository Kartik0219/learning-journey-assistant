import {
  BookOpen,
  LayoutDashboard,
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

  return (
    <div className="app-shell">
      <aside className={menuOpen ? 'sidebar sidebar--open' : 'sidebar'}>
        <NavLink className="brand" to="/" aria-label="Learning Journey Assistant dashboard" onClick={closeMenu}>
          <span className="brand-mark"><BookOpen size={18} aria-hidden="true" /></span>
          <span>Learning Journey<br />Assistant</span>
        </NavLink>
        <button
          className="sidebar-toggle"
          type="button"
          aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
          aria-expanded={menuOpen}
          aria-controls="primary-navigation"
          onClick={() => setMenuOpen((open) => !open)}
        >
          {menuOpen ? <X size={20} aria-hidden="true" /> : <Menu size={20} aria-hidden="true" />}
        </button>
        <nav className="navigation" id="primary-navigation" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, to }) => (
            <NavLink className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'} key={label} to={to} end={to === '/'} onClick={closeMenu}>
              <Icon size={17} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
        <div className="student-profile"><span className="avatar">AL</span><span><strong>Alex Lee</strong><small>Undergraduate</small></span></div>
      </aside>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/results" element={<ResultsOverviewPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  )
}

export default App
