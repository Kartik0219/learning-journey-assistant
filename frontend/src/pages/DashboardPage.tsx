import { useEffect, useMemo, useState } from 'react'
import { BookOpen, Info, Target } from 'lucide-react'
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { LearningOutcome } from '../data/dashboard'
import { buildStudentDashboardSubjects, performanceBand } from '../data/studentDashboard'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'

function getPriorityOutcomeIndex(outcomes: LearningOutcome[]) {
  return outcomes.reduce(
    (lowestIndex, outcome, index, allOutcomes) => outcome.masteryPercentage < allOutcomes[lowestIndex].masteryPercentage ? index : lowestIndex,
    0,
  )
}

export function DashboardPage() {
  const { studentId, results } = useStudent()
  const subjects = useMemo(() => buildStudentDashboardSubjects(results), [results])
  const subjectCodes = useMemo(() => Object.keys(subjects), [subjects])

  const [subjectCode, setSubjectCode] = useState(subjectCodes[0])
  const activeCode = subjects[subjectCode] ? subjectCode : subjectCodes[0]
  const subject = subjects[activeCode]
  const [selectedOutcomeIndex, setSelectedOutcomeIndex] = useState(0)

  // Re-point the evidence card at the weakest outcome when the data changes.
  useEffect(() => {
    setSelectedOutcomeIndex(getPriorityOutcomeIndex(subjects[activeCode].learningOutcomes))
  }, [subjects, activeCode])

  const selectedOutcome = subject.learningOutcomes[selectedOutcomeIndex] ?? subject.learningOutcomes[0]
  const trendData = subject.masteryTrend.map((mastery, index) => ({ cycle: index + 1, mastery }))
  const band = performanceBand(subject.overallMasteryPercentage)
  const selectedSiloId = (selectedOutcome?.name ?? '').split(' · ')[0]

  return <main className="dashboard" id="dashboard">
    <header className="dashboard-header results-header">
      <div><p className="eyebrow">Student {studentId} · learning journey</p><h1>Mastery dashboard <span className="title-subject">{activeCode}</span></h1></div>
      <div className="header-actions">
        <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={subjectCodes.map((code) => ({ value: code, label: subjects[code].label }))} onChange={setSubjectCode} />
      </div>
      <div className="header-spacer" aria-hidden="true" />
    </header>
    <div className="dash-top">
      <section className="stats" aria-label="Mastery summary">
        <article className="stat-card mastery-stat"><strong>{subject.overallMasteryPercentage}%</strong><span>Overall mastery estimate</span></article>
        <article className="stat-card focus-stat"><strong className={band === 'Fail' ? 'band-fail' : 'band-pass'}>{band}</strong><span>Performance <span className="label-nowrap">band<span className="tip"><button className="tip__trigger" type="button" aria-label="How the performance band is decided" aria-describedby="mastery-band-tip"><Info size={14} aria-hidden="true" /></button><span className="tip__pop" id="mastery-band-tip" role="tooltip">The subject's weighted total mapped to a grade band: below 50% Fail, 50–59% Pass, 60–69% Credit, 70–79% Distinction, 80% and above High Distinction. Formative only — not an official grade.</span></span></span></span></article>
        <article className="stat-card focus-stat"><strong>{subject.priorityFocusAreas}</strong><span className="label-nowrap">Priority focus areas<span className="tip"><button className="tip__trigger" type="button" aria-label="How priority focus areas are decided" aria-describedby="focus-areas-tip"><Info size={14} aria-hidden="true" /></button><span className="tip__pop" id="focus-areas-tip" role="tooltip">A SILO counts as a focus area when its weighted mastery is under 65% — not yet Proficient. Mastery is the score-and-weight average of the assessments that test it.</span></span></span></article>
        <article className="stat-card assessment-stat"><strong>{subject.assessmentsAnalysed}</strong><span>Assessments analysed</span></article>
      </section>
      <section className="panel trend-panel"><div className="panel-heading"><h2>Cumulative weighted mastery</h2><p>Your mastery so far, updated after each assessment.</p></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><LineChart data={trendData} margin={{ top: 6, right: 12, bottom: 4, left: 4 }}><CartesianGrid stroke="#eef1f8" vertical={false} /><XAxis dataKey="cycle" tickFormatter={(value) => `A${value}`} tick={{ fill: '#5a6178', fontSize: 11, fontWeight: 600 }} tickLine={false} tickMargin={8} axisLine={{ stroke: '#dfe4f0' }} /><YAxis width={38} domain={[0, 100]} ticks={[0, 50, 100]} tickFormatter={(value) => `${value}%`} tick={{ fill: '#9aa1b8', fontSize: 10 }} tickLine={false} axisLine={false} /><Tooltip cursor={{ stroke: '#c7cfe4', strokeDasharray: 4 }} formatter={(value) => [`${value}%`, 'Mastery']} labelFormatter={(label) => `Assessment ${label}`} /><Line dataKey="mastery" type="monotone" stroke="#00806e" strokeWidth={3} dot={{ r: 4, fill: '#00a38c', stroke: '#ffffff', strokeWidth: 2 }} activeDot={{ r: 5 }} /></LineChart></ResponsiveContainer></div><p className="chart-axis-label">Assessment number</p></section>
    </div>
    <div className="content-grid">
      <section className="panel outcomes-panel"><div className="panel-heading"><h2>Mastery by learning outcome</h2><p>Weighted from every assessment that tests each SILO. Select one to see the evidence.</p><ul className="mastery-legend" aria-label="Mastery band colour key"><li><span className="legend-dot atRisk" aria-hidden="true" />&lt;50% At risk</li><li><span className="legend-dot developing" aria-hidden="true" />50–65% Developing</li><li><span className="legend-dot proficient" aria-hidden="true" />65–80% Proficient</li><li><span className="legend-dot mastered" aria-hidden="true" />≥80% Mastered</li></ul></div>
        <div className="outcome-list">{subject.learningOutcomes.map((outcome, index) => <button aria-pressed={selectedOutcomeIndex === index} className={selectedOutcomeIndex === index ? 'outcome selected' : 'outcome'} key={outcome.name} onClick={() => setSelectedOutcomeIndex(index)} type="button"><span className="outcome-name">{outcome.name}</span><span className={`status ${outcome.status}`}>{outcome.statusLabel}</span><span className="progress-track"><span className={`progress-fill ${outcome.status}`} style={{ width: `${outcome.masteryPercentage}%` }} /></span><strong className="outcome-percentage">{outcome.masteryPercentage}%</strong></button>)}</div>
        <article className="evidence-card" aria-live="polite"><p className="evidence-label">Evidence</p><h3>{selectedOutcome.name}</h3><p className="evidence-meta">{selectedOutcome.masteryPercentage}% mastery · {selectedOutcome.statusLabel}</p><div className="evidence-block"><p>Assessments result and feedback</p><ul className="feedback-list">{(selectedOutcome.assessments ?? []).map((item, index) => <li key={item.name}><details open={index === 0}><summary><span className="fb-title">{item.name} · {item.weightPct}%</span><span className="fb-score">{item.score}/100</span></summary><div className="fb-silos">{item.silos.map((siloId) => <span key={siloId} className={siloId === selectedSiloId ? 'fb-silo current' : 'fb-silo'}>{siloId}</span>)}</div><q>{item.feedback}</q></details></li>)}</ul></div><div className="recommended-action"><Target size={18} aria-hidden="true" /><span>{selectedOutcome.recommendedAction}</span></div></article>
      </section>
      <div className="right-column">
        <section className="panel"><div className="panel-heading"><h2>Next steps for <span className="silo-tag">{selectedSiloId}</span></h2><p>{selectedOutcome.name} · {selectedOutcome.statusLabel} ({selectedOutcome.masteryPercentage}%)</p></div><ol className="steps">{(selectedOutcome.nextSteps ?? []).map((step, index) => <li key={step.text}><span>{index + 1}</span><p>{step.text}{step.emphasis && <strong>{step.emphasis}</strong>}{step.suffix}</p></li>)}</ol></section>
        <section className="panel"><div className="panel-heading"><h2>Recommended resources for <span className="silo-tag">{selectedSiloId}</span></h2><p>{selectedOutcome.name}</p></div><ul className="resources">{(selectedOutcome.recommendedResources ?? []).map((resource) => <li key={resource}><span /><a href="#resources">{resource}</a></li>)}</ul></section>
      </div>
    </div>
    <footer>Formative mastery estimates for {studentId}, derived from assessment results. Not official grades.</footer>
  </main>
}
