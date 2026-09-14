import { api, masteryBand } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

const STATUS_TONE: Record<string, string> = { Mastered: 'mastered', 'On Track': 'proficient', 'Focus Area': 'developing' }

export function AiInsightPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.aiInsight(studentId), studentId)

  if (loading) return <p className="page-status">Asking the AI for a second opinion… this can take up to 20 seconds.</p>
  if (error) return <PageError error={error} />
  if (!data) return null

  const insight = data.insight

  return (
    <main className="page" id="ai-insight">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · AI insight</p>
          <h1>A written second opinion</h1>
        </div>
      </header>
      <p className="sub page-lede">A plain-language reading of your results from a large language model. Your dashboard, calculated locally from your marked work, stays the source of truth.</p>

      {!data.enabled ? (
        <section className="panel"><h2>AI analysis is not enabled</h2><p className="empty-note">This deployment runs on the local, explainable analysis engine only. Your Dashboard and Study plan have the full breakdown.</p></section>
      ) : data.error ? (
        <section className="panel"><h2>AI analysis could not be completed</h2><p className="error-note">{data.error}</p><p className="sub">Your Dashboard is unaffected — it never depends on AI.</p></section>
      ) : insight && (
        <div className="grid2">
          <section className="panel">
            <div className="panel-head"><h2>Competency overview</h2></div>
            <div className="outcomes">
              {insight.learningOutcomes.map((lo) => {
                const tone = STATUS_TONE[lo.status] ?? masteryBand(lo.masteryPercentage).status
                return (
                  <div className="outcome static" key={lo.code}>
                    <span className="outcome-name"><strong>{lo.code}</strong> · {lo.title}</span>
                    <span className="outcome-pct">{Math.round(lo.masteryPercentage)}% <span className={`chip ${tone}`}>{lo.status}</span></span>
                    <span className="bar"><span className={`bar-fill ${tone}`} style={{ width: `${lo.masteryPercentage}%` }} /></span>
                    {lo.evidenceQuote && <q className="quote">{lo.evidenceQuote}</q>}
                  </div>
                )
              })}
            </div>
          </section>
          <div className="stack">
            {insight.strengths.length > 0 && (
              <section className="panel"><div className="panel-head"><h2>Strengths</h2></div><ul className="plain-list">{insight.strengths.map((s) => <li key={s}>{s}</li>)}</ul></section>
            )}
            {insight.focusAreas.length > 0 && (
              <section className="panel">
                <div className="panel-head"><h2>Suggested next steps</h2><p className="sub">Written by the AI — check them against your subject materials.</p></div>
                <ol className="steps">
                  {insight.focusAreas.map((fa, index) => (
                    <li key={fa.topic}><span className="step-n">{index + 1}</span><span><strong>{fa.topic}</strong> — {fa.recommendedStep} <span className="sub">({fa.resourceLinkOrModule})</span></span></li>
                  ))}
                </ol>
              </section>
            )}
            <p className="footer-note">{insight.disclaimer}</p>
          </div>
        </div>
      )}
    </main>
  )
}
