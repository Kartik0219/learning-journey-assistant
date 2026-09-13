import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Info, Target } from 'lucide-react'
import { api, masteryBand, type Outcome } from '../api'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

const FOCUS_THRESHOLD = 65

export function DashboardPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.dashboard(studentId), studentId)

  const subjectCodes = useMemo(() => data?.subjects.map((s) => s.code) ?? [], [data])
  const [subjectCode, setSubjectCode] = useState('')
  const activeCode = subjectCodes.includes(subjectCode) ? subjectCode : subjectCodes[0]
  const outcomes: Outcome[] = useMemo(
    () => (data?.outcomes ?? []).filter((o) => o.subject_code === activeCode && o.mastery_pct !== null),
    [data, activeCode],
  )
  const [selectedId, setSelectedId] = useState<number | null>(null)

  // Point the evidence card at the weakest outcome whenever the data changes.
  useEffect(() => {
    if (outcomes.length) {
      setSelectedId([...outcomes].sort((a, b) => (a.mastery_pct ?? 0) - (b.mastery_pct ?? 0))[0].id)
    }
  }, [outcomes])

  if (loading) return <p className="page-status">Loading dashboard…</p>
  if (error) return <PageError error={error} />
  if (!data || !activeCode) return <p className="page-status">No mastery has been estimated for {studentLabel} yet.</p>

  const subject = data.subjects.find((s) => s.code === activeCode)!
  const focusAreas = outcomes.filter((o) => (o.mastery_pct ?? 0) < FOCUS_THRESHOLD).length
  const selected = outcomes.find((o) => o.id === selectedId) ?? outcomes[0]
  const band = masteryBand(subject.average_mastery_pct)

  return <main className="dashboard" id="dashboard">
    <header className="dashboard-header results-header">
      <div><p className="eyebrow">{studentLabel} · learning journey</p><h1>Mastery dashboard <span className="title-subject">{activeCode}</span></h1></div>
      <div className="header-actions">
        {subjectCodes.length > 1 && <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={subjectCodes.map((code) => ({ value: code, label: code }))} onChange={setSubjectCode} />}
      </div>
      <div className="header-spacer" aria-hidden="true" />
    </header>
    <section className="stats" aria-label="Mastery summary">
      <article className="stat-card mastery-stat"><strong>{subject.average_mastery_pct}%</strong><span>Overall mastery estimate</span></article>
      <article className="stat-card focus-stat"><strong className={band.status === 'atRisk' ? 'band-fail' : 'band-pass'}>{band.label}</strong><span>Mastery band</span></article>
      <article className="stat-card focus-stat"><strong>{focusAreas}</strong><span className="label-nowrap">Priority focus areas<span className="tip"><button className="tip__trigger" type="button" aria-label="How priority focus areas are decided" aria-describedby="focus-areas-tip"><Info size={14} aria-hidden="true" /></button><span className="tip__pop" id="focus-areas-tip" role="tooltip">A SILO counts as a focus area when its mastery estimate is under {FOCUS_THRESHOLD}%. Estimates come from your marked results and reviewed skill gaps. Formative only — not an official grade.</span></span></span></article>
      <article className="stat-card assessment-stat"><strong>{outcomes.length}</strong><span>Outcomes tracked</span></article>
    </section>
    <div className="content-grid">
      <section className="panel outcomes-panel"><div className="panel-heading"><h2>Mastery by learning outcome</h2><p>Select an outcome to see the evidence behind its number.</p><ul className="mastery-legend" aria-label="Mastery band colour key"><li><span className="legend-dot atRisk" aria-hidden="true" />&lt;50% At risk</li><li><span className="legend-dot developing" aria-hidden="true" />50–65% Developing</li><li><span className="legend-dot proficient" aria-hidden="true" />65–80% Proficient</li><li><span className="legend-dot mastered" aria-hidden="true" />≥80% Mastered</li></ul></div>
        <div className="outcome-list">{outcomes.map((outcome) => {
          const pct = outcome.mastery_pct ?? 0
          const { status, label } = masteryBand(pct)
          return <button aria-pressed={selected?.id === outcome.id} className={selected?.id === outcome.id ? 'outcome selected' : 'outcome'} key={outcome.id} onClick={() => setSelectedId(outcome.id)} type="button"><span className="outcome-name">{outcome.code} · {outcome.description}</span><span className={`status ${status}`}>{label}</span><span className="progress-track"><span className={`progress-fill ${status}`} style={{ width: `${pct}%` }} /></span><strong className="outcome-percentage">{pct}%</strong></button>
        })}</div>
        {selected && <article className="evidence-card" aria-live="polite"><p className="evidence-label">Evidence</p><h3>{selected.code} · {selected.description}</h3><p className="evidence-meta">{selected.mastery_pct}% mastery · {masteryBand(selected.mastery_pct ?? 0).label}</p>
          {selected.explanation && <p>{selected.explanation}</p>}
          <div className="evidence-block"><p>Marker feedback behind this estimate</p>
            {selected.gaps.length ? <ul className="feedback-list">{selected.gaps.map((gap, index) => <li key={index}><details open={index === 0}><summary><span className="fb-title">{gap.severity} severity</span><span className="fb-score">{Math.round(gap.confidence * 100)}% confidence</span></summary><q>{gap.evidence}</q></details></li>)}</ul>
              : <p>No reviewed skill gaps for this outcome — nothing in your feedback flags it.</p>}
          </div>
          {selected.recommendation && <div className="recommended-action"><Target size={18} aria-hidden="true" /><span>{selected.recommendation.method}</span></div>}
        </article>}
      </section>
      <div className="right-column">
        <section className="panel"><div className="panel-heading"><h2>Priority topics</h2><p>Your lowest-scoring outcomes across every subject.</p></div><ol className="steps">{data.priority_outcomes.map((o, index) => <li key={o.id}><span>{index + 1}</span><p><strong>{o.code} ({o.subject_code}) · {o.mastery_pct}%</strong> — {o.description}</p></li>)}</ol></section>
        {selected?.recommendation && <section className="panel"><div className="panel-heading"><h2>Recommended material for <span className="silo-tag">{selected.code}</span></h2><p>{selected.recommendation.source_title ?? 'Subject material'}</p></div><p className="material-text">{selected.recommendation.material_text}</p></section>}
      </div>
    </div>
    <footer>Formative mastery estimates for {studentLabel}, derived from marked assessment results. Not official grades.</footer>
  </main>
}
