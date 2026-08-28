import {
  BookOpen,
  ChartNoAxesCombined,
  ClipboardList,
  FileQuestion,
  LayoutDashboard,
  LibraryBig,
  TableProperties,
} from 'lucide-react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { ResultsOverviewPage } from './pages/ResultsOverviewPage'
import './App.css'

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Results overview', icon: TableProperties, to: '/results' },
  { label: 'My plan', icon: ClipboardList },
  { label: 'Quizzes', icon: FileQuestion },
  { label: 'Resources', icon: LibraryBig },
  { label: 'Progress', icon: ChartNoAxesCombined },
]

function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <NavLink className="brand" to="/" aria-label="Learning Journey Assistant dashboard">
          <span className="brand-mark"><BookOpen size={18} aria-hidden="true" /></span>
          <span>Learning Journey<br />Assistant</span>
        </NavLink>
        <nav className="navigation" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, to }) => to ? (
            <NavLink className={({ isActive }) => isActive ? 'nav-item active' : 'nav-item'} key={label} to={to} end={to === '/'}>
              <Icon size={17} aria-hidden="true" />
              {label}
            </NavLink>
          ) : (
            <button className="nav-item" key={label} type="button"><Icon size={17} aria-hidden="true" />{label}</button>
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
