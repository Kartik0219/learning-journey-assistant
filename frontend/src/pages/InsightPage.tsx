import { useState } from 'react'
import { Sparkles } from 'lucide-react'
import { api, type AiInsight } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

/** Optional LLM second opinion, fetched only when asked, with a hard timeout. */
function AiSecondOpinion({ studentId }: { studentId: number }) {
  const [state, setState] = useState<'idle' | 'loading' | 'done' | 'failed'>('idle')
  const [data, setData] = useState<AiInsight | null>(null)
  const [failure, setFailure] = useState<string>('')

  async function ask() {
    setState('loading')
    try {
      setData(await api.aiInsight(studentId))
      setState('done')
    } catch (err) {
      setFailure(err instanceof Error && err.name === 'TimeoutError'
        ? 'The AI service did not answer within 30 seconds.'
        : 'The AI service could not be reached.')
      setState('failed')
    }
  }

  return (
    <section className="panel">
      <div className="panel-head">
        <h2>Optional: an AI second opinion</h2>
        <p className="sub">A large language model's reading of the same results. Slower, sometimes unavailable, and never the source of truth — the summary above is.</p>
      </div>
      {state === 'idle' && <div><button className="btn" type="button" onClick={ask}><Sparkles size={15} aria-hidden="true" /> Ask the AI</button></div>}
      {state === 'loading' && <p className="page-status">Asking… up to 30 seconds.</p>}
      {state === 'failed' && <p className="empty-note">{failure} Nothing above depends on it — try again later if you like.</p>}
      {state === 'done' && data && (
        !data.enabled ? <p className="empty-note">AI analysis is not enabled on this deployment.</p>
        : data.error ? <p className="empty-note">{data.error}</p>
        : data.insight && (
          <div className="stack">
            {data.insight.strengths.length > 0 && <div><h3 className="h3">Strengths</h3><ul className="plain-list">{data.insight.strengths.map((s) => <li key={s}>{s}</li>)}</ul></div>}
            {data.insight.focusAreas.length > 0 && (
              <div>
                <h3 className="h3">Suggested next steps</h3>
                <ol className="steps">{data.insight.focusAreas.map((fa, i) => <li key={fa.topic}><span className="step-n">{i + 1}</span><span><strong>{fa.topic}</strong> — {fa.recommendedStep}</span></li>)}</ol>
              </div>
            )}
            <p className="footer-note">{data.insight.disclaimer}</p>
          </div>
        )
      )}
    </section>
  )
}

export function InsightPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.insight(studentId), studentId)

  if (loading) return <p className="page-status">Reading your results…</p>
  if (error) return <PageError error={error} />
  if (!data) return null

  return (
    <main className="page" id="insight">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · insight</p>
          <h1>Where you stand, in plain words</h1>
          <p className="sub">Written by the app from your {data.generated_from.assessments} marked assessments across {data.generated_from.subjects} subjects — no AI, always available. Every number here is one you can check on Results.</p>
        </div>
      </header>

      <section className={`callout tone-${data.average_tone}`}>
        <p className="callout-text">{data.headline}</p>
        {data.average_total !== null && <span className={`chip ${data.average_tone}`}>{data.average_band}</span>}
      </section>

      <div className="grid2">
        <div className="stack">
          {data.subjects.map((s) => (
            <section className="panel" key={s.code}>
              <div className="panel-head subject-head">
                <h2>{s.code}</h2>
                {s.total !== null && <span className="subject-total">{s.total.toFixed(2)} <span className={`chip ${s.tone}`}>{s.band}</span></span>}
              </div>
              <div className="prose">{s.paragraphs.map((p, i) => <p key={i}>{p}</p>)}</div>
              {s.weakest_outcomes.length > 0 && (
                <p className="sub">Focus: {s.weakest_outcomes.map((o) => <span key={o.code} className="silo-tag focus-tag">{o.code} · {o.mastery_pct}%</span>)}</p>
              )}
            </section>
          ))}
        </div>

        <div className="stack">
          {data.this_week.length > 0 && (
            <section className="panel">
              <div className="panel-head"><h2>This week</h2><p className="sub">Three or four concrete moves, from your own numbers.</p></div>
              <ol className="steps">{data.this_week.map((step, i) => <li key={i}><span className="step-n">{i + 1}</span><span>{step}</span></li>)}</ol>
            </section>
          )}
          {data.themes.length > 0 && (
            <section className="panel">
              <div className="panel-head"><h2>What your markers keep saying</h2><p className="sub">Phrases that recur across your feedback, and what to do about each.</p></div>
              <div className="themes">
                {data.themes.map((t) => (
                  <article className="theme" key={t.label}>
                    <p className="theme-head"><strong>{t.label}</strong><span className="chip neutral">{t.count}×</span></p>
                    <p>{t.advice}</p>
                  </article>
                ))}
              </div>
            </section>
          )}
          <AiSecondOpinion studentId={studentId} />
        </div>
      </div>
      <footer className="footer-note">Formative only. This reading is arithmetic on your recorded marks and your markers' comments; it is not an official grade or academic advice.</footer>
    </main>
  )
}
