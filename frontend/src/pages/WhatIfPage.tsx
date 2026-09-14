import { useMemo, useState } from 'react'
import { RotateCcw } from 'lucide-react'
import { api, assessmentName, performanceBand, usesWeights, type SubjectResults } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

const TARGETS = [
  { label: 'Pass', min: 50 },
  { label: 'Credit', min: 60 },
  { label: 'Distinction', min: 70 },
  { label: 'High Distinction', min: 80 },
]

function clamp(n: number) { return Math.max(0, Math.min(100, n)) }

function SubjectCalculator({ subject }: { subject: SubjectResults }) {
  const rows = subject.assessments
  const actualTotal = rows.reduce((t, r) => t + (r.score ?? 0) * (r.weight ?? 0), 0)
  const unmarked = rows.filter((r) => r.score === null)
  const weightSum = rows.reduce((t, r) => t + (r.weight ?? 0), 0)

  const [scores, setScores] = useState<Record<number, number | null>>(() => Object.fromEntries(rows.map((r) => [r.id, r.score])))
  const [target, setTarget] = useState(() => {
    const next = TARGETS.find((t) => t.min > actualTotal)
    return (next ?? TARGETS[TARGETS.length - 1]).min
  })

  const whatIfTotal = rows.reduce((t, r) => t + (scores[r.id] ?? 0) * (r.weight ?? 0), 0)
  const actualBand = performanceBand(actualTotal)
  const whatIfBand = performanceBand(whatIfTotal)
  const targetLabel = TARGETS.find((t) => t.min === target)!.label
  const changed = rows.some((r) => scores[r.id] !== r.score)

  // For each assessment: the mark needed there, holding everything else at
  // its actual (or, if unmarked, its what-if) value, to reach the target.
  const routes = useMemo(() => rows.map((r) => {
    const w = r.weight ?? 0
    if (w === 0) return null
    const others = rows.reduce((t, o) => o.id === r.id ? t : t + ((o.score ?? scores[o.id] ?? 0) * (o.weight ?? 0)), 0)
    const needed = (target - others) / w
    return { row: r, needed, feasible: needed <= 100 }
  }).filter((x): x is { row: typeof rows[number]; needed: number; feasible: boolean } => x !== null), [rows, scores, target])

  const feasible = routes.filter((r) => r.feasible).sort((a, b) => a.needed - b.needed)
  const easiest = feasible[0]
  const spread = weightSum > 0 ? (target - actualTotal) / weightSum : null

  return (
    <section className="panel">
      <div className="panel-head subject-head">
        <div>
          <h2>{subject.code}</h2>
          <p className="sub">{subject.name}</p>
        </div>
        <label className="target">
          <span className="sub">I'm aiming for</span>
          <select value={target} onChange={(e) => setTarget(Number(e.target.value))} id={`target-${subject.code}`}>
            {TARGETS.map((t) => <option key={t.min} value={t.min}>{t.label} (≥{t.min})</option>)}
          </select>
        </label>
      </div>

      <div className="table-wrap">
        <table className="results-table whatif-table">
          <thead><tr><th>Assessment</th><th>Weight</th><th>Your mark</th><th>What if…</th><th>Counts for</th></tr></thead>
          <tbody>
            {rows.map((r) => {
              const w = r.weight ?? 0
              const s = scores[r.id]
              return (
                <tr key={r.id} className={s !== r.score ? 'edited' : ''}>
                  <td><strong>{assessmentName(r.assessment)}</strong>{r.score === null && <span className="chip neutral">not yet marked</span>}</td>
                  <td>{Math.round(w * 100)}%</td>
                  <td>{r.score ?? '—'}</td>
                  <td>
                    <input
                      id={`whatif-${r.id}`}
                      type="number" min={0} max={100} step={1}
                      aria-label={`What-if mark for ${assessmentName(r.assessment)}`}
                      value={s ?? ''}
                      placeholder="0"
                      onChange={(e) => setScores({ ...scores, [r.id]: e.target.value === '' ? null : clamp(Number(e.target.value)) })}
                    />
                  </td>
                  <td>{((s ?? 0) * w).toFixed(2)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>

      <div className="whatif-totals">
        <div className="stat"><span className="stat-value">{actualTotal.toFixed(2)}</span><span className="stat-label">Actual total · <span className={`chip ${actualBand.status}`}>{actualBand.label}</span></span></div>
        <div className={`stat ${changed ? 'edited' : ''}`}><span className="stat-value">{whatIfTotal.toFixed(2)}</span><span className="stat-label">What-if total · <span className={`chip ${whatIfBand.status}`}>{whatIfBand.label}</span></span></div>
        <button className="btn ghost" type="button" disabled={!changed} onClick={() => setScores(Object.fromEntries(rows.map((r) => [r.id, r.score])))}><RotateCcw size={14} aria-hidden="true" /> Reset</button>
      </div>

      <div className="routes">
        {actualTotal >= target ? (
          <p className="ok-note">You already have a {targetLabel} in {subject.code} on your recorded marks.</p>
        ) : (
          <>
            {unmarked.length > 0 && (
              <p>
                <strong>Still to come:</strong> {unmarked.map((r) => assessmentName(r.assessment)).join(', ')} ({Math.round(unmarked.reduce((t, r) => t + (r.weight ?? 0), 0) * 100)}% of the subject). Type a mark in <em>What if…</em> to see where it lands you.
              </p>
            )}
            {easiest ? (
              <p>
                <strong>Easiest single route to a {targetLabel}:</strong> {Math.ceil(easiest.needed)} on the {assessmentName(easiest.row.assessment)} ({Math.round((easiest.row.weight ?? 0) * 100)}%), keeping everything else as it is
                {easiest.row.score !== null && <> — that is {Math.ceil(easiest.needed) - easiest.row.score} more than your {easiest.row.score}</>}.
              </p>
            ) : (
              <p><strong>A {targetLabel} is out of reach from one assessment alone</strong> — no single mark up to 100 gets there while the others stay as they are.</p>
            )}
            {spread !== null && spread > 0 && (
              <p><strong>Or spread it out:</strong> about {Math.ceil(spread)} more marks on every assessment would do it.</p>
            )}
            {unmarked.length === 0 && (
              <p className="sub">All of your {subject.code} assessments are already marked, so this is for understanding the weights — which assessment mattered most, and what a retake or next attempt would need.</p>
            )}
          </>
        )}
      </div>
    </section>
  )
}

export function WhatIfPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.results(studentId), `results-${studentId}`)

  if (loading) return <p className="page-status">Loading your marks…</p>
  if (error) return <PageError error={error} />

  const subjects = (data?.subjects ?? []).filter((s) => usesWeights(s.assessments))
  const skipped = (data?.subjects ?? []).length - subjects.length

  return (
    <main className="page" id="what-if">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · what if</p>
          <h1>What do I need?</h1>
          <p className="sub">Pick the grade you want in each subject and see what it takes — a single mark that would get you there, or a smaller lift across everything. Change any mark to try a scenario; nothing you type is saved or sent anywhere.</p>
        </div>
      </header>
      {subjects.length === 0
        ? <section className="panel"><p className="empty-note">Your subjects have no assessment weights recorded, so totals cannot be projected.</p></section>
        : <div className="stack">{subjects.map((s) => <SubjectCalculator subject={s} key={s.code} />)}</div>}
      {skipped > 0 && <p className="footer-note">{skipped} subject{skipped === 1 ? '' : 's'} without recorded weights not shown.</p>}
      <footer className="footer-note">Formative only. Bands follow La Trobe's grade thresholds (Pass 50, Credit 60, Distinction 70, High Distinction 80) applied to the weighted total; official grades may include hurdles and moderation this calculator does not know about.</footer>
    </main>
  )
}
