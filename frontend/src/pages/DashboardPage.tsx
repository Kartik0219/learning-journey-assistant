import { useState } from 'react'
import { Target } from 'lucide-react'
import { Line, LineChart, ResponsiveContainer, Tooltip } from 'recharts'
import { dashboardSubjects, type LearningOutcome } from '../data/dashboard'

function getPriorityOutcomeIndex(outcomes: LearningOutcome[]) {
  return outcomes.reduce(
    (lowestIndex, outcome, index, allOutcomes) => outcome.masteryPercentage < allOutcomes[lowestIndex].masteryPercentage ? index : lowestIndex,
    0,
  )
}

export function DashboardPage() {
  const [subjectCode, setSubjectCode] = useState('STA101')
  const subject = dashboardSubjects[subjectCode]
  const [selectedOutcomeIndex, setSelectedOutcomeIndex] = useState(() => getPriorityOutcomeIndex(dashboardSubjects.STA101.learningOutcomes))
  const selectedOutcome = subject.learningOutcomes[selectedOutcomeIndex]
  const trendData = subject.masteryTrend.map((mastery, index) => ({ cycle: index + 1, mastery }))

  function handleSubjectChange(nextSubjectCode: string) {
    setSubjectCode(nextSubjectCode)
    setSelectedOutcomeIndex(getPriorityOutcomeIndex(dashboardSubjects[nextSubjectCode].learningOutcomes))
  }

  return <main className="dashboard" id="dashboard">
    <header className="dashboard-header">
      <div><p className="eyebrow">Learning progress</p><h1>Mastery dashboard</h1></div>
      <div className="header-actions">
        <label className="subject-picker"><span className="sr-only">Choose subject</span><select value={subjectCode} onChange={(event) => handleSubjectChange(event.target.value)}>{Object.values(dashboardSubjects).map((dashboardSubject) => <option value={dashboardSubject.code} key={dashboardSubject.code}>{dashboardSubject.label}</option>)}</select></label>
        <p className="formative-note"><span /> Formative, not an official grade</p>
      </div>
    </header>
    <section className="stats" aria-label="Mastery summary">
      <article className="stat-card mastery-stat"><strong>{subject.overallMasteryPercentage}%</strong><span>Overall mastery estimate</span></article>
      <article className="stat-card focus-stat"><strong>{subject.priorityFocusAreas}</strong><span>Priority focus areas</span></article>
      <article className="stat-card assessment-stat"><strong>{subject.assessmentsAnalysed}</strong><span>Assessments analysed</span></article>
    </section>
    <div className="content-grid">
      <section className="panel outcomes-panel"><div className="panel-heading"><h2>Mastery by learning outcome</h2><p>Select an outcome to see the evidence behind it.</p></div>
        <div className="outcome-list">{subject.learningOutcomes.map((outcome, index) => <button aria-pressed={selectedOutcomeIndex === index} className={selectedOutcomeIndex === index ? 'outcome selected' : 'outcome'} key={outcome.name} onClick={() => setSelectedOutcomeIndex(index)} type="button"><span className="outcome-name">{outcome.name}</span><span className={`status ${outcome.status}`}>{outcome.statusLabel}</span><span className="progress-track"><span className={`progress-fill ${outcome.status}`} style={{ width: `${outcome.masteryPercentage}%` }} /></span><strong className="outcome-percentage">{outcome.masteryPercentage}%</strong></button>)}</div>
        <article className="evidence-card" aria-live="polite"><p className="evidence-label">Evidence</p><h3>{selectedOutcome.name}</h3><p className="evidence-meta">{selectedOutcome.masteryPercentage}% mastery · {selectedOutcome.statusLabel}</p><div className="evidence-block"><p>From your results</p>{selectedOutcome.evidence.map((item) => <div className="evidence-row" key={item.label}><span>{item.label}</span><strong>{item.score}</strong></div>)}</div><div className="evidence-block"><p>From your feedback</p><q>{selectedOutcome.feedback}</q></div><div className="recommended-action"><Target size={18} aria-hidden="true" /><span>{selectedOutcome.recommendedAction}</span></div></article>
      </section>
      <div className="right-column"><section className="panel trend-panel"><div className="panel-heading"><h2>Progress trend</h2><p>Overall mastery across assessment cycles.</p></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={trendData}><Tooltip cursor={false} formatter={(value) => [`${value}%`, 'Mastery']} labelFormatter={(label) => `Cycle ${label}`} /><Line dataKey="mastery" type="monotone" stroke="#00806e" strokeWidth={3} dot={{ r: 4, fill: '#00a38c', stroke: '#ffffff', strokeWidth: 2 }} /></LineChart></ResponsiveContainer></div><div className="chart-caption"><span>Cycle 1</span><span>Now</span></div></section>
        <section className="panel"><div className="panel-heading"><h2>Your next steps</h2><p>Targeted at your two priority gaps.</p></div><ol className="steps">{subject.nextSteps.map((step, index) => <li key={step.text}><span>{index + 1}</span><p>{step.text}{step.emphasis && <strong>{step.emphasis}</strong>}{step.suffix}</p></li>)}</ol></section>
        <section className="panel"><div className="panel-heading"><h2>Recommended resources</h2><p>Chosen for the outcomes you are closing.</p></div><ul className="resources">{subject.recommendedResources.map((resource) => <li key={resource}><span /><a href="#resources">{resource}</a></li>)}</ul></section>
      </div>
    </div>
    <footer>Illustrative example. Mastery estimates are formative indicators, not official grades.</footer>
  </main>
}
