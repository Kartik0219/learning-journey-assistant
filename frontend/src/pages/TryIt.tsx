import { useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { assessmentName, performanceBand, type SubjectResults } from '../api'

/* Drag-a-mark sliders for one subject, under the Today strip. Every move
   recomputes the weighted total the same way the What-if page does; the
   parent drives the gauge from `onTotal`. Nothing is saved or sent. */

export function tryItTotal(subject: SubjectResults, scores: Record<number, number>): number {
  return subject.assessments.reduce((t, r) => t + (scores[r.id] ?? r.score ?? 0) * (r.weight ?? 0), 0)
}

export function TryIt({ subject, onTotal }: { subject: SubjectResults; onTotal: (total: number | null) => void }) {
  const rows = subject.assessments.filter((r) => (r.weight ?? 0) > 0)
  const [scores, setScores] = useState<Record<number, number>>({})
  const actual = tryItTotal(subject, {})
  const total = tryItTotal(subject, scores)
  const changed = rows.filter((r) => scores[r.id] !== undefined && scores[r.id] !== r.score)
  const band = performanceBand(total)
  const diff = total - actual

  function set(id: number, value: number) {
    const next = { ...scores, [id]: value }
    setScores(next)
    const t = tryItTotal(subject, next)
    onTotal(Math.abs(t - actual) < 0.005 ? null : t)
  }
  function reset() {
    setScores({})
    onTotal(null)
  }

  return (
    <div className="tryit" aria-label={`Try different marks in ${subject.code}`}>
      <p className="tryit-head">
        <strong>Try it</strong> — drag a mark in {subject.code} and watch the total move.
        {changed.length > 0 && <button type="button" className="link-btn" onClick={reset}><RotateCcw size={13} aria-hidden="true" /> Reset</button>}
      </p>
      <ul className="tryit-rows">
        {rows.map((r) => {
          const value = scores[r.id] ?? r.score ?? 0
          const edited = scores[r.id] !== undefined && scores[r.id] !== r.score
          return (
            <li key={r.id} className={edited ? 'tryit-row edited' : 'tryit-row'}>
              <label htmlFor={`try-${r.id}`}>
                <span className="tryit-name">{assessmentName(r.assessment)}</span>
                <span className="tryit-meta">{Math.round((r.weight ?? 0) * 100)}% · your mark {r.score ?? '—'}</span>
              </label>
              <input id={`try-${r.id}`} type="range" min={0} max={100} step={1} value={value} onChange={(e) => set(r.id, Number(e.target.value))} aria-valuetext={`${value} out of 100`} />
              <output htmlFor={`try-${r.id}`} className={edited ? 'tryit-value edited' : 'tryit-value'}>{value}</output>
            </li>
          )
        })}
      </ul>
      <p className="tryit-result" aria-live="polite">
        {changed.length === 0
          ? <>Your recorded marks give <strong>{actual.toFixed(2)}</strong> — {performanceBand(actual).label}.</>
          : <>With {changed.slice(0, 2).map((r, i) => <span key={r.id}>{i > 0 && ' and '}<strong>{scores[r.id]}</strong> on the {assessmentName(r.assessment)}</span>)}{changed.length > 2 && ` and ${changed.length - 2} more`}, {subject.code} would be <strong>{total.toFixed(2)}</strong> — <span className={`chip ${band.status}`}>{band.label}</span> <span className={diff >= 0 ? 'delta up' : 'delta down'}>{diff >= 0 ? '+' : ''}{diff.toFixed(2)}</span></>}
      </p>
    </div>
  )
}
