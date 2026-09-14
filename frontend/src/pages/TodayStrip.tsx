import { ArrowRight, Calculator } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, type InsightSubject } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'

// Same thresholds as performanceBand / the backend's BANDS.
const BANDS: [number, string][] = [[50, 'Pass'], [60, 'Credit'], [70, 'Distinction'], [80, 'High Distinction']]

function nextBand(total: number): { label: string; gap: number } | null {
  const up = BANDS.find(([min]) => min > total)
  return up ? { label: up[1], gap: Math.round((up[0] - total) * 100) / 100 } : null
}

/** A ring showing the subject total out of 100, coloured by its band. */
function Gauge({ value, tone, label }: { value: number; tone: string; label: string }) {
  const r = 40
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value))
  return (
    <svg className={`gauge tone-${tone}`} viewBox="0 0 100 100" role="img" aria-label={`${value.toFixed(2)} out of 100, ${label}`}>
      <circle className="gauge-track" cx="50" cy="50" r={r} />
      <circle className="gauge-fill" cx="50" cy="50" r={r} strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 50 50)" />
      <text className="gauge-value" x="50" y="47">{value.toFixed(1)}</text>
      <text className="gauge-label" x="50" y="64">{label}</text>
    </svg>
  )
}

/**
 * The ten-second view. A student between classes needs one number that
 * matters this week, one lever, and one thing to do - not a report. All of
 * it comes from the Insight computation, so it is deterministic and instant.
 */
export function TodayStrip() {
  const { studentId } = useStudent()
  const { data } = useApi(() => api.insight(studentId), `insight-${studentId}`)
  if (!data) return null

  const scored = data.subjects.filter((s): s is InsightSubject & { total: number } => s.total !== null)
  if (!scored.length) return null
  const weakest = scored.reduce((a, b) => (b.total < a.total ? b : a))
  const up = nextBand(weakest.total)
  const lever = weakest.biggest_lever
  const step = data.this_week[0]

  return (
    <section className={`today tone-${weakest.tone}`} aria-label="What matters today">
      <Gauge value={weakest.total} tone={weakest.tone} label={weakest.band} />
      <div className="today-main">
        <p className="eyebrow">Today</p>
        <h2 className="today-line">
          {up
            ? <><span className="title-subject">{weakest.code}</span> is <strong>{up.gap}</strong> mark{up.gap === 1 ? '' : 's'} off a {up.label}.</>
            : <>Every subject is already at a <strong>{weakest.band}</strong> or better.</>}
        </h2>
        {lever && (
          <p className="today-sub">
            Biggest lever: the <strong>{lever.assessment}</strong> ({Math.round(lever.weight * 100)}%) — every 10 marks there moves the total by {Math.round(lever.weight * 100) / 10}.
          </p>
        )}
        {step && <p className="today-step"><span className="step-n">1</span><span>{step}</span></p>}
      </div>
      <div className="today-actions">
        <Link className="btn" to="/study">Start studying <ArrowRight size={15} aria-hidden="true" /></Link>
        <Link className="btn ghost" to="/insight/what-if"><Calculator size={15} aria-hidden="true" /> What do I need?</Link>
      </div>
    </section>
  )
}
