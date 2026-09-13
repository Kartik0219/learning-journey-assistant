import { useState } from 'react'
import { CheckCircle2, Eye } from 'lucide-react'
import { api, masteryBand, type Outcome } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

// Backend method keys ("spaced_practice") -> "Spaced practice".
function humanise(key: string): string {
  const text = key.replace(/_/g, ' ')
  return text.charAt(0).toUpperCase() + text.slice(1)
}

function PlanCard({ outcome, canPractise, onPractised }: { outcome: Outcome; canPractise: boolean; onPractised: () => void }) {
  const [revealed, setRevealed] = useState(false)
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const pct = outcome.mastery_pct ?? 0
  const { status, label } = masteryBand(pct)
  const rec = outcome.recommendation!

  async function practise() {
    setSaving(true)
    try {
      await api.markPractised(rec.id)
      setDone(true)
      onPractised()
    } finally {
      setSaving(false)
    }
  }

  return <section className="panel plan-card">
    <div className="panel-heading"><h2>{outcome.code} <span className="silo-tag">{outcome.subject_code}</span> <span className={`status ${status}`}>{label} · {pct}%</span></h2><p>{outcome.description}</p></div>
    <p><strong>Recommended method:</strong> {humanise(rec.method)}</p>
    <p className="material-text">{rec.material_text}</p>
    {rec.source_title && <p className="evidence-meta">Grounded in: {rec.source_title}</p>}
    {outcome.quiz_questions.length > 0 && <div className="evidence-block">
      <p>Practice questions</p>
      <ol className="steps">{outcome.quiz_questions.map((q, index) => <li key={q.id}><span>{index + 1}</span><p>{q.question_text}{revealed && q.answer_text && <><br /><em>Model answer{q.answer_title ? ` (${q.answer_title})` : ''}:</em> {q.answer_text}</>}</p></li>)}</ol>
      {!revealed && <button className="plan-btn plan-btn--ghost" type="button" onClick={() => setRevealed(true)}><Eye size={15} aria-hidden="true" /> Reveal model answers</button>}
    </div>}
    {canPractise && <button className="plan-btn" type="button" disabled={saving || done} onClick={practise}><CheckCircle2 size={15} aria-hidden="true" /> {done ? 'Marked as practised' : saving ? 'Saving…' : 'Mark as practised'}</button>}
  </section>
}

export function StudyPlanPage() {
  const { session, studentId, studentLabel } = useStudent()
  const { data, error, loading, reload } = useApi(() => api.dashboard(studentId), studentId)

  if (loading && !data) return <p className="page-status">Loading study plan…</p>
  if (error) return <PageError error={error} />

  const planned = (data?.outcomes ?? [])
    .filter((o) => o.recommendation && o.mastery_pct !== null)
    .sort((a, b) => (a.mastery_pct ?? 0) - (b.mastery_pct ?? 0))

  return (
    <main className="dashboard" id="study-plan">
      <header className="dashboard-header results-header">
        <div>
          <p className="eyebrow">{studentLabel} · study plan</p>
          <h1>Study plan</h1>
        </div>
        <div className="header-spacer" aria-hidden="true" />
      </header>
      {planned.length === 0
        ? <p className="page-status">No study recommendations yet — they appear once your results have been analysed.</p>
        : planned.map((outcome) => <PlanCard key={outcome.id} outcome={outcome} canPractise={session.role === 'student'} onPractised={reload} />)}
      <footer>Weakest outcomes first. Every recommendation and question is built from your own feedback and subject materials — not generated from nothing. Formative only.</footer>
    </main>
  )
}
