import {
  BookOpen,
  BrainCircuit,
  Library,
  LayoutDashboard,
  ListChecks,
  LogOut,
  Menu,
  Sparkles,
  TableProperties,
  UserRound,
  X,
} from 'lucide-react'
import { useState } from 'react'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { AiInsightPage } from './pages/AiInsightPage'
import { DashboardPage } from './pages/DashboardPage'
import { QuizzesPage } from './pages/QuizzesPage'
import { ResourcesPage } from './pages/ResourcesPage'
import { ResultsOverviewPage } from './pages/ResultsOverviewPage'
import { StudyPlanPage } from './pages/StudyPlanPage'
import { StudentProvider, useStudent } from './studentContext'
import './App.css'

const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Results', icon: TableProperties, to: '/results' },
  { label: 'Study plan', icon: Sparkles, to: '/study-plan' },
  { label: 'Quizzes', icon: ListChecks, to: '/quizzes' },
  { label: 'Resources', icon: Library, to: '/resources' },
  { label: 'AI Insight', icon: BrainCircuit, to: '/ai-insight' },
]

function AppShell() {
  const [menuOpen, setMenuOpen] = useState(false)
  const { studentLabel } = useStudent()
  const closeMenu = () => setMenuOpen(false)

  return (
    <div className="shell">
      <div className="chrome">
        <header className="topbar">
          <NavLink className="brand" to="/" aria-label="Learning Journey Assistant dashboard" onClick={closeMenu}>
            <span className="brand-mark"><BookOpen size={16} aria-hidden="true" /></span>
            <span className="brand-name">Learning Journey Assistant</span>
          </NavLink>
          <div className="topbar-user">
            <span className="student-pill"><UserRound size={14} aria-hidden="true" /> {studentLabel}</span>
            {/* Real sign-out: clears the Flask session server-side. */}
            <a className="logout-btn" href="/logout"><LogOut size={15} aria-hidden="true" /> Log out</a>
          </div>
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
        </header>
        <nav className={menuOpen ? 'navbar navbar--open' : 'navbar'} id="primary-navigation" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, to }) => (
            <NavLink className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')} key={label} to={to} end={to === '/'} onClick={closeMenu}>
              <Icon size={16} aria-hidden="true" />
              {label}
            </NavLink>
          ))}
        </nav>
      </div>
      <p className="banner"><strong>Formative only</strong> — nothing here changes your official grade or is sent to Moodle.</p>
      <Routes>
        <Route path="/" element={<DashboardPage />} />
        <Route path="/results" element={<ResultsOverviewPage />} />
        <Route path="/study-plan" element={<StudyPlanPage />} />
        <Route path="/quizzes" element={<QuizzesPage />} />
        <Route path="/resources" element={<ResourcesPage />} />
        <Route path="/ai-insight" element={<AiInsightPage />} />
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
