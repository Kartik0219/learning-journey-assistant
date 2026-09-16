import { useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { BookOpen, Info } from 'lucide-react'
import {
  api,
  assessmentName,
  humanise,
  masteryBand,
  masteryPct,
  performanceBand,
  subjectTotal,
  usesWeights,
  weightedAverage,
  type Outcome,
  type ResultRow,
} from '../api'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'
import { MiniBars, MiniDots, MiniRing, MiniScale, QuickActions, greeting } from './Minis'
import { TodayStrip } from './TodayStrip'
import { TrendChart } from './TrendChart'

const FOCUS_THRESHOLD = 65

function fmt(value: number, digits = 1) {
  return value.toFixed(digits)
}

function Evidence({ outcome, rows }: { outcome: Outcome; rows: ResultRow[] }) {
  const pct = masteryPct(outcome) ?? 0
  const band = masteryBand(pct)
  const weighted = usesWeights(rows)
  const totalWeight = rows.reduce((sum, r) => sum + (r.weight ?? 0), 0)
  const calc = rows.length && weighted
    ? `(${rows.map((r) => `${r.score}×${Math.round((r.weight ?? 0) * 100)}%`).join(' + ')}) ÷ ${Math.round(totalWeight * 100)}% = ${fmt(weightedAverage(rows) ?? 0, 2)}%`
    : null

  return (
    <article className="evidence" aria-live="polite">
      <p className="evidence-label">Evidence</p>
      <h3>{outcome.code} · {outcome.description}</h3>
      <p className="evidence-meta">{fmt(pct)}% mastery · {band.label}</p>
      {rows.length > 0 ? (
        <ul className="ev-list">
          {rows.map((row, index) => (
            <li key={row.id}>
              <details open={index === 0}>
                <summary>
                  <span>{assessmentName(row.assessment)}{row.weight ? ` · ${Math.round(row.weight * 100)}%` : ''}</span>
                  <span className="ev-score">{row.score ?? '—'}/100</span>
                </summary>
                <div className="ev-body">
                  <div className="silo-chips">
                    {row.silo_codes.map((code) => <span key={code} className={code === outcome.code ? 'current' : ''}>{code}</span>)}
                  </div>
                  {row.feedback && <q>{row.feedback}</q>}
                </div>
              </details>
            </li>
          ))}
        </ul>
      ) : outcome.gaps.length > 0 ? (
        <ul className="ev-list">
          {outcome.gaps.map((gap, index) => (
            <li key={index}><details open={index === 0}><summary><span>{humanise(gap.severity)} severity gap</span><span className="ev-score">{Math.round(gap.confidence * 100)}% confidence</span></summary><div className="ev-body"><q>{gap.evidence}</q></div></details></li>
          ))}
        </ul>
      ) : (
        <p className="evidence-meta">No marked results or reviewed skill gaps point to this outcome yet.</p>
      )}
      {calc ? <p className="calc">{calc}</p> : outcome.explanation && <p className="calc">{outcome.explanation}</p>}
    </article>
  )
}

function NextSteps({ outcome, rows }: { outcome: Outcome; rows: ResultRow[] }) {
  const pct = masteryPct(outcome) ?? 0
  const band = masteryBand(pct)
  const rec = outcome.recommendation
  const scored = rows.filter((r) => r.score !== null)
  const lowest = [...scored].sort((a, b) => (a.score ?? 0) - (b.score ?? 0))[0]
  const heaviest = [...scored].sort((a, b) => (b.weight ?? 0) - (a.weight ?? 0))[0]

  const steps: ReactNode[] = []
  if (lowest) steps.push(<>Rework <strong>{assessmentName(lowest.assessment)}</strong> — your lowest mark here ({lowest.score}/100) — with its {outcome.code} feedback open beside you.</>)
  if (heaviest?.weight && heaviest !== lowest) steps.push(<>Prioritise {outcome.code} before the <strong>{assessmentName(heaviest.assessment)}</strong>: it carries {Math.round(heaviest.weight * 100)}% of the subject.</>)
  if (outcome.quiz_questions.length) steps.push(<>Take a practice quiz on {outcome.code} ({outcome.quiz_questions.length} question{outcome.quiz_questions.length === 1 ? '' : 's'} built from your own gaps).</>)
  if (rec) steps.push(<>When you have worked through it, mark the {outcome.code} step as practised on your Study plan.</>)

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Next steps for <span className="silo-tag">{outcome.code}</span></h2>
        <p className="sub">{outcome.description} · {band.label} ({fmt(pct)}%)</p>
      </div>
      {rec && <div className="method-row"><span className="chip brand">{humanise(rec.method)}</span><span className="sub">chosen from the fixed study-method table</span></div>}
      {steps.length > 0 && <ol className="steps">{steps.map((step, index) => <li key={index}><span className="step-n">{index + 1}</span><span>{step}</span></li>)}</ol>}
      {rec && (rec.source_title
        ? (
          <div className="material">
            <p className="material-title">From “{rec.source_title}”{rec.source_provenance === 'curated' && <span className="chip muted">curated</span>}</p>
            <p>{rec.material_text}</p>
            {rec.source_url && <a className="material-link" href={rec.source_url} target="_blank" rel="noopener noreferrer">Open resource ↗</a>}
          </div>
        )
        : <p className="empty-note">{rec.material_text} Nothing is made up in its place.</p>)}
    </section>
  )
}

export function DashboardPage() {
  const { studentId, studentLabel } = useStudent()
  const dash = useApi(() => api.dashboard(studentId), studentId)
  const res = useApi(() => api.results(studentId), `results-${studentId}`)

  const subjectCodes = useMemo(() => dash.data?.subjects.map((s) => s.code) ?? [], [dash.data])
  const [subjectCode, setSubjectCode] = useState('')
  const activeCode = subjectCodes.includes(subjectCode) ? subjectCode : subjectCodes[0]
  const outcomes = useMemo(
    () => (dash.data?.outcomes ?? []).filter((o) => o.subject_code === activeCode && o.mastery_score !== null),
    [dash.data, activeCode],
  )
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [revealed, setRevealed] = useState(false)
  const evidenceRef = useRef<HTMLDivElement>(null)

  // Open the evidence for the weakest outcome whenever the subject changes.
  useEffect(() => {
    if (outcomes.length) setSelectedId([...outcomes].sort((a, b) => (a.mastery_score ?? 0) - (b.mastery_score ?? 0))[0].id)
  }, [outcomes])

  // Bars grow in from empty whenever the subject changes, instead of just
  // appearing at their final width - a small cue that this is fresh data.
  useEffect(() => {
    setRevealed(false)
    const id = requestAnimationFrame(() => setRevealed(true))
    return () => cancelAnimationFrame(id)
  }, [activeCode])

  // Left/right arrow keys step through subjects, as long as the focus is not
  // in a text field, textarea or select (so typing "→" in a search box never
  // gets hijacked).
  useEffect(() => {
    if (subjectCodes.length < 2) return
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName
      if (tag === 'INPUT' || tag === 'TEXTAREA' || tag === 'SELECT' || (e.target as HTMLElement | null)?.isContentEditable) return
      if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
      const i = subjectCodes.indexOf(activeCode)
      if (i === -1) return
      const next = subjectCodes[(i + (e.key === 'ArrowRight' ? 1 : -1) + subjectCodes.length) % subjectCodes.length]
      setSubjectCode(next)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [subjectCodes, activeCode])

  if (dash.loading || res.loading) return <p className="page-status">Loading your dashboard…</p>
  if (dash.error) return <PageError error={dash.error} />
  if (res.error) return <PageError error={res.error} />
  if (!dash.data || !activeCode) return <p className="page-status">No mastery has been estimated for {studentLabel} yet.</p>

  const subjectResults = res.data?.subjects.find((s) => s.code === activeCode)
  const rows = subjectResults?.assessments ?? []
  const total = subjectResults ? subjectTotal(subjectResults) : null
  const band = total === null ? null : performanceBand(total)
  const focusAreas = outcomes.filter((o) => (masteryPct(o) ?? 0) < FOCUS_THRESHOLD).length
  const selected = outcomes.find((o) => o.id === selectedId) ?? outcomes[0]
  const tagged = (o: Outcome) => rows.filter((r) => r.silo_codes.includes(o.code))

  // Jump to an assessment picked on the trend chart: select the weakest
  // outcome it evidences (usually the one the student is looking at the
  // chart to understand), then scroll the evidence panel into view.
  function jumpToAssessment(row: ResultRow) {
    const candidates = outcomes.filter((o) => row.silo_codes.includes(o.code))
    const target = [...candidates].sort((a, b) => (a.mastery_score ?? 0) - (b.mastery_score ?? 0))[0]
    if (target) setSelectedId(target.id)
    // Instant, not smooth: smooth scrolling from a click handler is not
    // reliably honoured across browsers when it races a re-render, and a
    // jump that sometimes silently does nothing is worse than one that isn't animated.
    evidenceRef.current?.scrollIntoView({ block: 'center' })
  }

  return (
    <main className="page" id="dashboard">
      <header className="page-head">
        <div>
          <p className="eyebrow">{greeting()} · {studentLabel}</p>
          <h1>Where you stand in <span className="title-subject">{activeCode}</span></h1>
        </div>
        {subjectCodes.length > 1 && (
          <div className="subject-picker">
            <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={subjectCodes.map((code) => ({ value: code, label: code }))} onChange={setSubjectCode} />
            <p className="kbd-hint"><kbd>←</kbd> <kbd>→</kbd> to switch</p>
          </div>
        )}
      </header>

      <TodayStrip activeCode={activeCode} onPickSubject={setSubjectCode} />
      <QuickActions />

      <section className="stats" aria-label="Subject summary">
        <article className="stat">
          <span className="stat-row">
            <span className="stat-value">{total === null ? '—' : fmt(total, 2)}</span>
            {total !== null && <MiniRing value={total} />}
          </span>
          <span className="stat-label">{usesWeights(rows) ? 'Weighted subject total' : 'Average score'}</span>
        </article>
        <article className="stat">
          {band ? <span className={`chip ${band.status}`}>{band.label}</span> : <span className="stat-value">—</span>}
          {total !== null && <MiniScale value={total} />}
          <span className="stat-label">Performance band
            <span className="tip"><button className="tip__trigger" type="button" aria-label="How the performance band is decided" aria-describedby="band-tip"><Info size={13} aria-hidden="true" /></button>
              <span className="tip__pop" id="band-tip" role="tooltip">The subject total mapped to a grade band: under 50 Fail, 50–59 Pass, 60–69 Credit, 70–79 Distinction, 80+ High Distinction. Formative only — not an official grade.</span></span>
          </span>
        </article>
        <article className="stat">
          <span className="stat-row">
            <span className="stat-value">{focusAreas}</span>
            <MiniDots pcts={outcomes.map((o) => masteryPct(o) ?? 0)} />
          </span>
          <span className="stat-label">Focus areas (under {FOCUS_THRESHOLD}%) · {outcomes.length} outcomes</span>
        </article>
        <article className="stat">
          <span className="stat-row">
            <span className="stat-value">{rows.length}</span>
            <MiniBars scores={rows.map((r) => r.score)} />
          </span>
          <span className="stat-label">Assessments analysed · scores in order</span>
        </article>
        {rows.length > 1 && <TrendChart rows={rows} onSelect={jumpToAssessment} />}
      </section>

      <div className="grid2">
        <section className="panel">
          <div className="panel-head">
            <h2>Mastery by learning outcome</h2>
            <p className="sub">Weighted from every assessment that tests each SILO. Select one to see the evidence.</p>
          </div>
          <ul className="legend" aria-label="Mastery band colour key">
            <li><span className="legend-dot atRisk" aria-hidden="true" />Under 50% at risk</li>
            <li><span className="legend-dot developing" aria-hidden="true" />50–65% developing</li>
            <li><span className="legend-dot proficient" aria-hidden="true" />65–80% proficient</li>
            <li><span className="legend-dot mastered" aria-hidden="true" />80%+ mastered</li>
          </ul>
          <div className="outcomes">
            {outcomes.map((outcome) => {
              const pct = masteryPct(outcome) ?? 0
              const { status, label } = masteryBand(pct)
              const isSelected = selected?.id === outcome.id
              return (
                <button type="button" key={outcome.id} aria-pressed={isSelected} className={isSelected ? 'outcome selected' : 'outcome'} onClick={() => setSelectedId(outcome.id)}>
                  <span className="outcome-name"><strong>{outcome.code}</strong> · {outcome.description}</span>
                  <span className="outcome-pct">{fmt(pct)}% <span className={`chip ${status}`}>{label}</span></span>
                  <span className="bar"><span className={`bar-fill ${status}`} style={{ width: revealed ? `${pct}%` : '0%' }} /></span>
                </button>
              )
            })}
          </div>
          {selected && <div ref={evidenceRef}><Evidence key={selected.id} outcome={selected} rows={tagged(selected)} /></div>}
        </section>

        <div className="stack">
          {selected && <NextSteps outcome={selected} rows={tagged(selected)} />}
          <section className="panel">
            <div className="panel-head">
              <h2>Priority topics</h2>
              <p className="sub">Your weakest outcomes across every subject.</p>
            </div>
            <ol className="steps">
              {dash.data.priority_outcomes.map((o, index) => (
                <li key={o.id}><span className="step-n">{index + 1}</span><span><strong>{o.code} · {o.subject_code}</strong> — {fmt(masteryPct(o) ?? 0)}% · {o.description}</span></li>
              ))}
            </ol>
          </section>
        </div>
      </div>
      <footer className="footer-note">Formative mastery estimates for {studentLabel}, built from your marked results. Not official grades.</footer>
    </main>
  )
}
