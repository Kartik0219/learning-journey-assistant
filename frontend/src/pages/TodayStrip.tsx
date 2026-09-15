import { useEffect, useState } from 'react'
import { ArrowRight, Calculator, Eye, SlidersHorizontal } from 'lucide-react'
import { Link } from 'react-router-dom'
import { api, performanceBand, type InsightSubject } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { TryIt } from './TryIt'
import { formatKey, keys, melbourneDateKey, readLocal, writeLocal, type LastVisit } from '../local'

// Same thresholds as performanceBand / the backend's BANDS.
const BANDS: [number, string][] = [[50, 'Pass'], [60, 'Credit'], [70, 'Distinction'], [80, 'High Distinction']]

function nextBand(total: number): { label: string; gap: number } | null {
  const up = BANDS.find(([min]) => min > total)
  return up ? { label: up[1], gap: Math.round((up[0] - total) * 100) / 100 } : null
}

/** A ring showing the subject total out of 100, coloured by its band. */
function Gauge({ value, tone, label, changed }: { value: number; tone: string; label: string; changed: boolean }) {
  const r = 40
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(100, value))
  return (
    <svg className={`gauge tone-${tone}${changed ? ' changed' : ''}`} viewBox="0 0 100 100" role="img" aria-label={`${value.toFixed(2)} out of 100, ${label}`}>
      <circle className="gauge-track" cx="50" cy="50" r={r} />
      <circle className="gauge-fill" cx="50" cy="50" r={r} strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 50 50)" />
      <text className="gauge-value" x="50" y="47">{value.toFixed(1)}</text>
      <text className="gauge-label" x="50" y="64">{label}</text>
    </svg>
  )
}

interface TodayStripProps {
  /** The subject the rest of the dashboard is showing (the picker's value). */
  activeCode?: string
  /** Switch the dashboard's subject picker - offered when the strip's
   *  subject is not the one on screen, so the two never look out of step. */
  onPickSubject?: (code: string) => void
}

/**
 * The ten-second view. A student between classes needs one number that
 * matters this week, one lever, and one thing to do - not a report. All of
 * it comes from the Insight computation, so it is deterministic and instant.
 *
 * The strip always shows the *most urgent* subject (lowest total across
 * every subject), which may differ from the subject picked for the page -
 * it says so, and offers to switch the page to match. "Try it" opens
 * sliders that drive the gauge live; nothing typed there is saved.
 */
export function TodayStrip({ activeCode, onPickSubject }: TodayStripProps = {}) {
  const { studentId } = useStudent()
  const { data } = useApi(() => api.insight(studentId), `insight-${studentId}`)
  const results = useApi(() => api.results(studentId), `results-${studentId}`)
  const [tryOpen, setTryOpen] = useState(false)
  const [tryTotal, setTryTotal] = useState<number | null>(null)
  const [since, setSince] = useState<LastVisit | null>(null)

  // "Since your last visit": remember today's totals once per Melbourne day.
  useEffect(() => {
    if (!data) return
    const prev = readLocal<LastVisit | null>(keys.last(studentId), null)
    const today = melbourneDateKey()
    if (prev && prev.at !== today) setSince(prev)
    if (!prev || prev.at !== today) {
      const totals = Object.fromEntries(data.subjects.filter((s) => s.total !== null).map((s) => [s.code, s.total as number]))
      writeLocal(keys.last(studentId), { at: today, totals })
    }
  }, [data, studentId])

  if (!data) return null

  const scored = data.subjects.filter((s): s is InsightSubject & { total: number } => s.total !== null)
  if (!scored.length) return null
  const weakest = scored.reduce((a, b) => (b.total < a.total ? b : a))
  const up = nextBand(weakest.total)
  const lever = weakest.biggest_lever
  const step = data.this_week[0]
  const differs = Boolean(activeCode && onPickSubject && weakest.code !== activeCode)
  const subjectRows = results.data?.subjects.find((s) => s.code === weakest.code)
  const canTry = Boolean(subjectRows && subjectRows.assessments.some((r) => (r.weight ?? 0) > 0))
  const shown = tryTotal ?? weakest.total
  const shownBand = tryTotal === null ? { status: weakest.tone, label: weakest.band } : performanceBand(tryTotal)
  const prevTotal = since?.totals[weakest.code]
  const delta = prevTotal === undefined ? null : Math.round((weakest.total - prevTotal) * 100) / 100

  return (
    <section className={`today tone-${shownBand.status}`} aria-label="What matters today">
      <Gauge key={Math.round(shown * 10)} value={shown} tone={shownBand.status} label={shownBand.label} changed={tryTotal !== null} />
      <div className="today-main">
        <p className="eyebrow">Today · most urgent of your {scored.length} subject{scored.length === 1 ? '' : 's'}</p>
        <h2 className="today-line">
          {tryTotal !== null
            ? <>With those marks, <span className="title-subject">{weakest.code}</span> would be <strong>{tryTotal.toFixed(1)}</strong> — {shownBand.label}.</>
            : up
              ? <><span className="title-subject">{weakest.code}</span> is <strong>{up.gap}</strong> mark{up.gap === 1 ? '' : 's'} off a {up.label}.</>
              : <>Every subject is already at a <strong>{weakest.band}</strong> or better.</>}
        </h2>
        {lever && (
          <p className="today-sub">
            Biggest lever: the <strong>{lever.assessment}</strong> ({Math.round(lever.weight * 100)}%) — every 10 marks there moves the total by {Math.round(lever.weight * 100) / 10}.
          </p>
        )}
        {step && <p className="today-step"><span className="step-n">1</span><span>{step}</span></p>}
        {since && delta !== null && (
          <p className="today-since">
            Since your last visit ({formatKey(since.at)}): {weakest.code} {delta === 0 ? 'unchanged' : <>{delta > 0 ? 'up' : 'down'} <strong>{Math.abs(delta).toFixed(2)}</strong></>}.
          </p>
        )}
        {differs && (
          <p className="today-switch">
            This page is showing <strong>{activeCode}</strong>.{' '}
            <button type="button" className="link-btn" onClick={() => onPickSubject?.(weakest.code)}>
              <Eye size={14} aria-hidden="true" /> Show {weakest.code} instead
            </button>
          </p>
        )}
      </div>
      <div className="today-actions">
        <Link className="btn" to="/study">Start studying <ArrowRight size={15} aria-hidden="true" /></Link>
        {canTry && (
          <button type="button" className="btn ghost" aria-expanded={tryOpen} onClick={() => { if (tryOpen) setTryTotal(null); setTryOpen((o) => !o) }}>
            <SlidersHorizontal size={15} aria-hidden="true" /> {tryOpen ? 'Hide sliders' : 'Try it: drag a mark'}
          </button>
        )}
        <Link className="btn ghost" to="/insight/what-if"><Calculator size={15} aria-hidden="true" /> What do I need?</Link>
      </div>
      {tryOpen && subjectRows && <TryIt subject={subjectRows} onTotal={setTryTotal} />}
    </section>
  )
}
