import { useEffect, useMemo, useRef, useState } from 'react'
import { BookOpen, Brain, ListChecks, Sparkles } from 'lucide-react'
import { buildStudentDashboardSubjects } from '../data/studentDashboard'
import { assessmentFingerprint, buildStudyPlan, type SiloPlan } from '../data/studyPlan'
import { loadSnapshot, saveSnapshot } from '../data/studyPlanStore'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'

type Stage = 'idle' | 'working' | 'ready'

function formatWhen(iso: string | null): string {
  if (!iso) return ''
  const date = new Date(iso)
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString([], { dateStyle: 'medium', timeStyle: 'short' })
}

export function StudyPlanPage() {
  const { studentId, results } = useStudent()
  const subjects = useMemo(() => buildStudentDashboardSubjects(results), [results])
  const subjectCodes = useMemo(() => Object.keys(subjects), [subjects])

  const [subjectCode, setSubjectCode] = useState(subjectCodes[0])
  const activeCode = subjects[subjectCode] ? subjectCode : subjectCodes[0]
  const [stage, setStage] = useState<Stage>('idle')
  const [tab, setTab] = useState<'summary' | 'plan'>('summary')
  const [plans, setPlans] = useState<SiloPlan[]>([])
  const [generatedAt, setGeneratedAt] = useState<string | null>(null)
  const [savedFingerprint, setSavedFingerprint] = useState<string | null>(null)
  const timer = useRef<number | undefined>(undefined)

  const currentFingerprint = assessmentFingerprint(subjects, activeCode)
  const isStale = savedFingerprint !== currentFingerprint

  // Load any saved snapshot for this student + subject before doing anything else.
  useEffect(() => {
    window.clearTimeout(timer.current)
    const saved = loadSnapshot(studentId, activeCode)
    if (saved) {
      setPlans(saved.plans)
      setGeneratedAt(saved.generatedAt)
      setSavedFingerprint(saved.sourceFingerprint)
      setStage('ready')
      setTab('plan')
    } else {
      setPlans([])
      setGeneratedAt(null)
      setSavedFingerprint(null)
      setStage('idle')
      setTab('summary')
    }
    return () => window.clearTimeout(timer.current)
  }, [studentId, activeCode])

  function run() {
    window.clearTimeout(timer.current)
    setStage('working')
    // Placeholder: one pass = AI summarises + maps feedback, then the plan is
    // assembled from the pre-built catalogue. No live model call yet.
    timer.current = window.setTimeout(() => {
      const fresh = buildStudyPlan(subjects, activeCode)
      const now = new Date().toISOString()
      setPlans(fresh)
      setGeneratedAt(now)
      setSavedFingerprint(currentFingerprint)
      setStage('ready')
      setTab('plan')
      saveSnapshot(studentId, { subjectCode: activeCode, generatedAt: now, sourceFingerprint: currentFingerprint, plans: fresh })
    }, 1000)
  }

  const ready = stage === 'ready'
  const canRun = stage !== 'working' && (stage === 'idle' || isStale)
  const buttonLabel = stage === 'working'
    ? 'Analysing…'
    : !ready
      ? 'Analyse and generate study plan'
      : isStale
        ? 'Regenerate study plan'
        : 'Study plan up to date'

  return <main className="dashboard" id="study-plan">
    <header className="dashboard-header results-header">
      <div><p className="eyebrow">Student {studentId} · study plan</p><h1>Study plan — powered by AI</h1></div>
      <div className="header-actions">
        <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={subjectCodes.map((code) => ({ value: code, label: subjects[code].label }))} onChange={setSubjectCode} />
      </div>
      <div className="header-spacer" aria-hidden="true" />
    </header>

    <div className="generate-row">
      <button className="generate-btn" type="button" onClick={run} disabled={!canRun}>
        <Sparkles size={16} aria-hidden="true" />
        {buttonLabel}
      </button>
      <span className="generate-hint">Summarises your marker feedback for {activeCode} and assembles a plan from the pre-built resource catalogue.</span>
    </div>

    {generatedAt && <p className="generate-meta">Generated {formatWhen(generatedAt)} · saved on this device · {isStale ? 'new assessment data available — regenerate to refresh' : 'up to date with your assessments'}</p>}

    <p className="ai-note"><Sparkles size={15} aria-hidden="true" /> AI is used only to summarise marker feedback and map it to SILOs. Resources, activities and quizzes are pre-built and lecturer-reviewed — not generated on request — so the plan stays grounded and consistent. Formative only.</p>

    {stage === 'idle' && <section className="panel plan-empty"><p>Nothing generated yet. Choose <strong>Analyse and generate study plan</strong> to summarise your feedback and build a plan.</p></section>}
    {stage === 'working' && <section className="panel plan-empty"><p>Summarising {activeCode} feedback, mapping it to each SILO, and assembling the plan…</p></section>}

    {ready && <>
      <div className="subtabs" role="tablist" aria-label="Study plan sections">
        <button className="subtab" type="button" role="tab" id="tab-summary" aria-controls="panel-summary" aria-selected={tab === 'summary'} onClick={() => setTab('summary')}>Feedback summary</button>
        <button className="subtab" type="button" role="tab" id="tab-plan" aria-controls="panel-plan" aria-selected={tab === 'plan'} onClick={() => setTab('plan')}>Study plan</button>
      </div>

      {tab === 'summary' && <section className="panel" role="tabpanel" id="panel-summary" aria-labelledby="tab-summary">
        <div className="panel-heading"><h2>Feedback summary by outcome</h2><p>AI-summarised marker feedback, mapped to each SILO. Expand a row for the source comments.</p></div>
        <ol className="plan-list">
          {plans.map((item) => <li className="plan-item" key={item.siloId}>
            <div className="plan-item__head"><span className="plan-silo">{item.silo}</span><span className={`status ${item.status}`}>{item.statusLabel} · {item.masteryPercentage}%</span></div>
            <p className="plan-weakness"><strong>Summary. </strong>{item.feedbackSummary}</p>
            <p className="plan-weakness"><strong>Mapped weakness. </strong>{item.weakness}</p>
            <div className="plan-steps"><p className="plan-steps__label">Source feedback</p><ul className="feedback-list">{item.assessments.map((a) => <li key={a.name}><details><summary><span className="fb-title">{a.name} · {a.weightPct}%</span><span className="fb-score">{a.score}/100</span></summary><q>{a.feedback}</q></details></li>)}</ul></div>
          </li>)}
        </ol>
      </section>}

      {tab === 'plan' && <section className="panel" role="tabpanel" id="panel-plan" aria-labelledby="tab-plan">
        <div className="panel-heading"><h2>Study plan · pre-built resources by outcome</h2><p>Selected per SILO from the reviewed subject catalogue — consistent and citable.</p></div>
        <ol className="plan-list">
          {plans.map((item) => <li className="plan-item plan-card" key={item.siloId}>
            <div className="plan-item__head"><span className="plan-silo">{item.silo}</span><span className={`status ${item.status}`}>{item.statusLabel} · {item.masteryPercentage}%</span></div>
            <div className="plan-group">
              <p className="plan-group__head"><BookOpen size={14} aria-hidden="true" />Recommended resources</p>
              <ul className="catalog-list">{item.resources.map((resource) => <li className="catalog-item" key={resource}><a href="#resources">{resource}</a></li>)}</ul>
            </div>
            <div className="plan-group">
              <p className="plan-group__head"><ListChecks size={14} aria-hidden="true" />Recommended activities</p>
              <ol className="steps">{item.activities.map((activity, index) => <li key={index}><span>{index + 1}</span><p>{activity}</p></li>)}</ol>
            </div>
            <div className="plan-group">
              <p className="plan-group__head"><Brain size={14} aria-hidden="true" />Adaptive quizzes</p>
              <ul className="catalog-list">{item.quizzes.map((quiz) => <li className="catalog-item" key={quiz}><a href="#quizzes">{quiz}</a></li>)}</ul>
            </div>
          </li>)}
        </ol>
      </section>}
    </>}

    <footer>Feedback summary is AI-assisted; resources, activities and quizzes are pre-built. Saved locally so it stays consistent between visits.</footer>
  </main>
}
