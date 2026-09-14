import { useState } from 'react'
import { CheckCircle2 } from 'lucide-react'
import { api, humanise, masteryBand, masteryPct, type Outcome } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

function PlanCard({ outcome, onPractised }: { outcome: Outcome; onPractised: () => void }) {
  const [saving, setSaving] = useState(false)
  const [done, setDone] = useState(false)
  const pct = masteryPct(outcome) ?? 0
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

  return (
    <section className="panel plan-card">
      <div className="plan-head">
        <div>
          <h2>{outcome.code} <span className="silo-tag">{outcome.subject_code}</span></h2>
          <p className="sub">{outcome.description}</p>
        </div>
        <span className="outcome-pct">{pct.toFixed(1)}% <span className={`chip ${status}`}>{label}</span></span>
      </div>
      <div className="method-row"><span className="chip brand">{humanise(rec.method)}</span><span className="sub">recommended study method</span></div>
      {rec.source_title
        ? (
          <div className="material">
            <p className="material-title">From “{rec.source_title}”{rec.source_provenance === 'curated' && <span className="chip muted">curated</span>}</p>
            <p>{rec.material_text}</p>
            {rec.source_url && <a className="material-link" href={rec.source_url} target="_blank" rel="noopener noreferrer">Open resource ↗</a>}
          </div>
        )
        : <p className="empty-note">{rec.material_text}</p>}
      <div>
        <button className="btn" type="button" disabled={saving || done} onClick={practise}>
          <CheckCircle2 size={15} aria-hidden="true" /> {done ? 'Marked as practised' : saving ? 'Saving…' : 'Mark as practised'}
        </button>
      </div>
    </section>
  )
}

export function StudyPlanPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading, reload } = useApi(() => api.dashboard(studentId), studentId)

  if (loading && !data) return <p className="page-status">Loading your study plan…</p>
  if (error) return <PageError error={error} />

  const planned = (data?.outcomes ?? [])
    .filter((o) => o.recommendation && o.mastery_score !== null)
    .sort((a, b) => (a.mastery_score ?? 0) - (b.mastery_score ?? 0))

  return (
    <main className="page" id="study-plan">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · study plan</p>
          <h1>What to study next</h1>
        </div>
      </header>
      {planned.length === 0
        ? <p className="page-status">No study recommendations yet — they appear once your results have been analysed.</p>
        : <div className="plan-grid">{planned.map((outcome) => <PlanCard key={outcome.id} outcome={outcome} onPractised={reload} />)}</div>}
      <footer className="footer-note">Weakest outcomes first. Study methods come from a fixed table, and material only ever comes from real subject passages. Marking a step practised gives a small, capped boost to that outcome.</footer>
    </main>
  )
}
