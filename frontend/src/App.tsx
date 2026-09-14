import {
  BookOpen,
  BrainCircuit,
  LayoutDashboard,
  LogOut,
  Sparkles,
  TableProperties,
} from 'lucide-react'
import type { ReactNode } from 'react'
import { Avatar } from './Avatar'
import { ThemeToggle } from './ThemeToggle'
import { NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { DashboardPage } from './pages/DashboardPage'
import { InsightPage } from './pages/InsightPage'
import { WhatIfPage } from './pages/WhatIfPage'
import { QuizzesPage } from './pages/QuizzesPage'
import { ResourcesPage } from './pages/ResourcesPage'
import { ResultsOverviewPage } from './pages/ResultsOverviewPage'
import { StudyPlanPage } from './pages/StudyPlanPage'
import { StudentProvider, useStudent } from './studentContext'
import './App.css'

// Four places to go. Quizzes and Resources are steps of the same journey as
// the plan (plan → read → test), and What if? is the question that follows
// "you are 9 marks short" - so they live as sub-tabs, not top-level tabs.
// On phones the same four render as a bottom tab bar (App.css).
const navigation = [
  { label: 'Dashboard', icon: LayoutDashboard, to: '/' },
  { label: 'Results', icon: TableProperties, to: '/results' },
  { label: 'Study', icon: Sparkles, to: '/study' },
  { label: 'Insight', icon: BrainCircuit, to: '/insight' },
]

const studyTabs = [
  { label: 'Plan', to: '/study' },
  { label: 'Quizzes', to: '/study/quizzes' },
  { label: 'Resources', to: '/study/resources' },
]
const insightTabs = [
  { label: 'Where I stand', to: '/insight' },
  { label: 'What if?', to: '/insight/what-if' },
]

function Tabbed({ tabs, label, children }: { tabs: { label: string; to: string }[]; label: string; children: ReactNode }) {
  return (
    <>
      <nav className="subnav" aria-label={label}>
        {tabs.map((t) => (
          <NavLink key={t.to} to={t.to} end className={({ isActive }) => (isActive ? 'subnav-item active' : 'subnav-item')}>{t.label}</NavLink>
        ))}
      </nav>
      {children}
    </>
  )
}

function AppShell() {
  const { studentLabel } = useStudent()

  return (
    <div className="shell">
      <div className="chrome">
        <header className="topbar">
          <NavLink className="brand" to="/" aria-label="Learning Journey Assistant dashboard">
            <span className="brand-mark"><BookOpen size={16} aria-hidden="true" /></span>
            <span className="brand-name">Learning Journey Assistant</span>
          </NavLink>
          <div className="topbar-user">
            <span className="student-pill"><Avatar seed={studentLabel} /> {studentLabel}</span>
            <ThemeToggle />
            {/* Real sign-out: clears the Flask session server-side. */}
            <a className="logout-btn" href="/logout"><LogOut size={15} aria-hidden="true" /> Log out</a>
          </div>
        </header>
        <nav className="navbar" id="primary-navigation" aria-label="Primary navigation">
          {navigation.map(({ label, icon: Icon, to }) => (
            <NavLink className={({ isActive }) => (isActive ? 'nav-item active' : 'nav-item')} key={label} to={to} end={to === '/'}>
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
        <Route path="/study" element={<Tabbed tabs={studyTabs} label="Study sections"><StudyPlanPage /></Tabbed>} />
        <Route path="/study/quizzes" element={<Tabbed tabs={studyTabs} label="Study sections"><QuizzesPage /></Tabbed>} />
        <Route path="/study/resources" element={<Tabbed tabs={studyTabs} label="Study sections"><ResourcesPage /></Tabbed>} />
        <Route path="/insight" element={<Tabbed tabs={insightTabs} label="Insight sections"><InsightPage /></Tabbed>} />
        <Route path="/insight/what-if" element={<Tabbed tabs={insightTabs} label="Insight sections"><WhatIfPage /></Tabbed>} />
        {/* Old addresses keep working for bookmarks, the docs and the videos. */}
        <Route path="/study-plan" element={<Navigate to="/study" replace />} />
        <Route path="/quizzes" element={<Navigate to="/study/quizzes" replace />} />
        <Route path="/resources" element={<Navigate to="/study/resources" replace />} />
        <Route path="/what-if" element={<Navigate to="/insight/what-if" replace />} />
        <Route path="/ai-insight" element={<Navigate to="/insight" replace />} />
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
