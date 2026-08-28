import { studentResults, studentSummary } from '../data/studentAssessments'

function formatPercentage(value: number) {
  return `${Math.round(value * 100)}%`
}

export function ResultsOverviewPage() {
  const assessmentCount = studentResults.reduce((count, subject) => count + subject.assessments.length, 0)

  return <main className="dashboard" id="results-overview">
    <header className="dashboard-header"><div><p className="eyebrow">Student assessment record</p><h1>Results overview</h1></div><p className="formative-note"><span /> Formative, not an official grade</p></header>
    <section className="stats" aria-label="Student assessment summary"><article className="stat-card mastery-stat"><strong>{studentSummary.averageTotal.toFixed(2)}%</strong><span>Average total</span></article><article className="stat-card focus-stat"><strong>{studentSummary.performanceBand}</strong><span>Performance band</span></article><article className="stat-card assessment-stat"><strong>{assessmentCount}</strong><span>Assessments recorded</span></article></section>
    <section className="results-panel" aria-labelledby="assessment-results-heading"><div className="panel-heading"><h2 id="assessment-results-heading">All assessment results</h2><p>{studentSummary.id} across {studentResults.length} subjects</p></div><div className="subject-results">{studentResults.map((subject) => <section className="subject-section" key={subject.code} aria-labelledby={`${subject.code}-heading`}><header className="subject-header"><div><p className="eyebrow">Subject</p><h3 id={`${subject.code}-heading`}>{subject.code}</h3></div><p className="subject-total"><span>Subject total</span><strong>{subject.total.toFixed(2)}%</strong></p></header><div className="table-scroll"><table><thead><tr><th scope="col">Assessment</th><th scope="col">Score</th><th scope="col">Feedback comment</th><th scope="col">SILO</th><th scope="col">Weight</th><th scope="col">Weighted score</th></tr></thead><tbody>{subject.assessments.map((assessment) => <tr key={assessment.assessment}><th scope="row">{assessment.assessment}</th><td><span className="score">{assessment.score}</span></td><td className="feedback">{assessment.feedback}</td><td className="silos">{assessment.silos}</td><td>{formatPercentage(assessment.weight)}</td><td className="weighted-score">{assessment.weightedScore.toFixed(2)}</td></tr>)}</tbody></table></div></section>)}</div></section>
    <footer>Source: CSE results workbook. Scores and feedback are presented for the selected student record.</footer>
  </main>
}
