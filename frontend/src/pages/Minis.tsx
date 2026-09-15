import { Link } from 'react-router-dom'
import { Calculator, Library, ListChecks, Sparkles } from 'lucide-react'
import { masteryBand, performanceBand, type MasteryStatus } from '../api'

/* Small inline visuals for the dashboard stat cards. Each draws only from
   data already on screen, so the picture never says more than the number. */

/** Ring of a total out of 100, in its performance-band colour. */
export function MiniRing({ value }: { value: number }) {
  const r = 15, c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value))
  const tone = performanceBand(value).status
  return (
    <svg className={`mini mini-ring tone-${tone}`} viewBox="0 0 40 40" aria-hidden="true">
      <circle className="mini-track" cx="20" cy="20" r={r} />
      <circle className="mini-fill" cx="20" cy="20" r={r} strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 20 20)" />
    </svg>
  )
}

/** The five grade thresholds as a scale, with a marker at the total. */
export function MiniScale({ value }: { value: number }) {
  const x = Math.max(0, Math.min(100, value))
  return (
    <svg className="mini mini-scale" viewBox="0 0 100 12" aria-hidden="true" preserveAspectRatio="none">
      <rect className="seg atRisk" x="0" y="4" width="50" height="4" />
      <rect className="seg developing" x="50" y="4" width="10" height="4" />
      <rect className="seg proficient" x="60" y="4" width="20" height="4" />
      <rect className="seg mastered" x="80" y="4" width="20" height="4" />
      <circle className="marker" cx={x} cy="6" r="3.2" />
    </svg>
  )
}

/** One dot per learning outcome, coloured by its mastery band. */
export function MiniDots({ pcts }: { pcts: number[] }) {
  return (
    <span className="mini mini-dots" aria-hidden="true">
      {pcts.map((p, i) => <i key={i} className={`dot ${masteryBand(p).status as MasteryStatus}`} title={`${p.toFixed(1)}%`} />)}
    </span>
  )
}

/** One bar per assessment score (0–100), in reading order. */
export function MiniBars({ scores }: { scores: (number | null)[] }) {
  const w = 100 / Math.max(scores.length, 1)
  return (
    <svg className="mini mini-bars" viewBox="0 0 100 24" aria-hidden="true" preserveAspectRatio="none">
      {scores.map((s, i) => {
        const h = s === null ? 0 : Math.max(2, (s / 100) * 22)
        return <rect key={i} className={`bar-s ${s === null ? 'none' : performanceBand(s).status}`} x={i * w + w * 0.15} y={24 - h} width={w * 0.7} height={h} rx="1" />
      })}
    </svg>
  )
}

/** Phone-width shortcut row under the Today strip; the tabs cover this on desktop. */
export function QuickActions() {
  const items = [
    { to: '/study', label: 'Plan', icon: Sparkles },
    { to: '/study/quizzes', label: 'Quiz', icon: ListChecks },
    { to: '/study/resources', label: 'Read', icon: Library },
    { to: '/insight/what-if', label: 'What if?', icon: Calculator },
  ]
  return (
    <nav className="quick" aria-label="Quick actions">
      {items.map(({ to, label, icon: Icon }) => (
        <Link key={to} to={to} className="quick-item"><span className="quick-icon"><Icon size={18} aria-hidden="true" /></span>{label}</Link>
      ))}
    </nav>
  )
}

/** "Good morning" by the viewer's clock; formative tone, no name (anonymised data). */
export function greeting(now = new Date()): string {
  const h = now.getHours()
  const part = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening'
  const day = now.toLocaleDateString(undefined, { weekday: 'long', day: 'numeric', month: 'long' })
  return `${part} · ${day}`
}
