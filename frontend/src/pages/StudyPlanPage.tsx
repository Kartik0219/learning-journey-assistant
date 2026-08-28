import { useEffect, useRef, useState } from 'react'
import { Sparkles } from 'lucide-react'
import { studentDashboardId, studentDashboardSubjects } from '../data/studentDashboard'
import { buildStudyPlan, studyPlanSubjectCodes } from '../data/studyPlan'

export function StudyPlanPage() {
  const [subjectCode, setSubjectCode] = useState(studyPlanSubjectCodes[0])
  const [status, setStatus] = useState<'idle' | 'analysing' | 'ready'>('idle')
  const timer = useRef<number | undefined>(undefined)
  const plans = buildStudyPlan(subjectCode)

  // Any subject change invalidates the current plan - ask the user to re-run.
  useEffect(() => {
    setStatus('idle')
    return () => window.clearTimeout(timer.current)
  }, [subjectCode])

  function handleGenerate() {
    setStatus('analysing')
    window.clearTimeout(timer.current)
    // Placeholder: simulate the analysis pass. No live model call yet.
    timer.current = window.setTimeout(() => setStatus('ready'), 900)
  }

  return <main className="dashboard" id="study-plan">
    <header className="dashboard-header results-header">
      <div><p className="eyebrow">Student {studentDashboardId} · AI study plan</p><h1>Study plan — powered by AI</h1></div>
      <div className="header-actions">
        <label className="subject-picker results-subject-picker"><span className="picker-label">Choose subject</span><select value={subjectCode} onChange={(event) => setSubjectCode(event.target.value)}>{studyPlanSubjectCodes.map((code) => <option value={code} key={code}>{studentDashboardSubjects[code].label}</option>)}</select></label>
      </div>
      <div className="header-spacer" aria-hidden="true" />
    </header>

    <div className="generate-row">
      <button className="generate-btn" type="button" onClick={handleGenerate} disabled={status === 'analysing'}>
        <Sparkles size={16} aria-hidden="true" />
        {status === 'analysing' ? 'Analysing…' : status === 'ready' ? 'Re-analyse & regenerate' : 'Analyse and generate study plan'}
      </button>
      <span className="generate-hint">Reads your marks and marker feedback for {subjectCode}.</span>
    </div>

    <p className="ai-note"><Sparkles size={15} aria-hidden="true" /> Placeholder — drafts are derived from your marks and marker feedback. Live AI generation is not connected yet. Formative only, not official advice.</p>

    {status === 'idle' && <section className="panel plan-empty"><p>No study plan yet. Select a subject and choose <strong>Analyse and generate study plan</strong>.</p></section>}

    {status === 'analysing' && <section className="panel plan-empty"><p>Analysing {subjectCode} results and feedback across every SILO…</p></section>}

    {status === 'ready' && <section className="panel">
      <div className="panel-heading"><h2>Weakness &amp; study plan by outcome</h2><p>For each SILO: what the AI reads as the gap, and how to close it.</p></div>
      <ol className="plan-list">
        {plans.map((item) => <li className="plan-item" key={item.siloId}>
          <div className="plan-item__head"><span className="plan-silo">{item.silo}</span><span className={`status ${item.status}`}>{item.statusLabel} · {item.masteryPercentage}%</span></div>
          <p className="plan-weakness"><strong>Identified weakness. </strong>{item.weakness}</p>
          <div className="plan-steps"><p className="plan-steps__label">Recommended study plan</p><ol className="steps">{item.plan.map((step, index) => <li key={index}><span>{index + 1}</span><p>{step}</p></li>)}</ol></div>
          <div className="plan-steps"><p className="plan-steps__label">Recommended resources</p><ul className="resources">{item.resources.map((resource) => <li key={resource}><span aria-hidden="true" /><a href="#resources">{resource}</a></li>)}</ul></div>
        </li>)}
      </ol>
    </section>}

    <footer>AI-assisted draft for {studentDashboardId}. Review with your teacher before relying on it.</footer>
  </main>
}
