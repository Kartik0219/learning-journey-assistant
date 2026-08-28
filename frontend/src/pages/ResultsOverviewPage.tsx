import { useState } from 'react'
import { studentResults, studentSummary } from '../data/studentAssessments'

function formatPercentage(value: number) {
  return `${Math.round(value * 100)}%`
}

function getPerformanceBand(total: number) {
  if (total < 50) return 'At risk'
  if (total < 60) return 'P range'
  if (total < 70) return 'C range'
  if (total < 80) return 'D range'
  return 'HD range'
}

export function ResultsOverviewPage() {
  const [selectedSubjectCode, setSelectedSubjectCode] = useState(studentResults[0].code)
  const selectedSubject = studentResults.find((subject) => subject.code === selectedSubjectCode)!
  const performanceBand = getPerformanceBand(selectedSubject.total)

  return <main className="dashboard" id="results-overview">
    <header className="dashboard-header results-header"><div><p className="eyebrow">Student assessment record</p><h1>Results overview</h1></div><div className="header-actions"><label className="subject-picker results-subject-picker"><span className="picker-label">Choose subject</span><select value={selectedSubjectCode} onChange={(event) => setSelectedSubjectCode(event.target.value)}>{studentResults.map((subject) => <option key={subject.code} value={subject.code}>{subject.code}</option>)}</select></label></div><div className="header-spacer" aria-hidden="true" /></header>
    <section className="stats" aria-label="Selected subject assessment summary"><article className="stat-card mastery-stat"><strong>{selectedSubject.total.toFixed(2)}%</strong><span>{selectedSubject.code} total</span></article><article className="stat-card focus-stat"><strong>{performanceBand}</strong><span>{selectedSubject.code} performance band</span></article><article className="stat-card assessment-stat"><strong>{selectedSubject.assessments.length}</strong><span>Assessments in {selectedSubject.code}</span></article></section>
    <section className="results-panel" aria-labelledby="assessment-results-heading"><div className="panel-heading"><h2 id="assessment-results-heading">Assessment results</h2><p>{studentSummary.id} · {selectedSubject.code}</p></div><div className="subject-results"><section className="subject-section" aria-labelledby={`${selectedSubject.code}-heading`}><header className="subject-header"><div><p className="eyebrow">Subject</p><h3 id={`${selectedSubject.code}-heading`}>{selectedSubject.code}</h3></div><p className="subject-total"><span>Subject total</span><strong>{selectedSubject.total.toFixed(2)}%</strong></p></header><div className="table-scroll"><table><thead><tr><th scope="col">Assessment</th><th scope="col">Score</th><th scope="col">Feedback comment</th><th scope="col">SILO</th><th scope="col">Weight</th><th scope="col">Weighted score</th></tr></thead><tbody>{selectedSubject.assessments.map((assessment) => <tr key={assessment.assessment}><th scope="row">{assessment.assessment}</th><td><span className="score">{assessment.score}</span></td><td className="feedback">{assessment.feedback}</td><td className="silos">{assessment.silos}</td><td>{formatPercentage(assessment.weight)}</td><td className="weighted-score">{assessment.weightedScore.toFixed(2)}</td></tr>)}</tbody></table></div></section></div></section>
    <footer>Source: CSE results workbook. Scores and feedback are presented for the selected student record.</footer>
  </main>
}
