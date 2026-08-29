import { useState } from 'react'
import { BookOpen, Info } from 'lucide-react'
import { assessmentMap, subjectSilos } from '../data/studentAssessments'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'

function formatPercentage(value: number) {
  return `${Math.round(value * 100)}%`
}

function getPerformanceBand(total: number) {
  if (total < 50) return 'Fail'
  if (total < 60) return 'Pass'
  if (total < 70) return 'Credit'
  if (total < 80) return 'Distinction'
  return 'High Distinction'
}

export function ResultsOverviewPage() {
  const { studentId, results } = useStudent()
  const [selectedSubjectCode, setSelectedSubjectCode] = useState(results[0].code)
  const selectedSubject = results.find((subject) => subject.code === selectedSubjectCode) ?? results[0]
  const performanceBand = getPerformanceBand(selectedSubject.total)
  const silos = subjectSilos[selectedSubject.code] ?? []
  const mapEntries = assessmentMap[selectedSubject.code] ?? []

  return <main className="dashboard" id="results-overview">
    <header className="dashboard-header results-header"><div><p className="eyebrow">Student assessment record</p><h1>Results overview <span className="title-subject">{selectedSubject.code}</span></h1></div><div className="header-actions"><Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={selectedSubject.code} options={results.map((subject) => ({ value: subject.code, label: subject.code }))} onChange={setSelectedSubjectCode} /></div><div className="header-spacer" aria-hidden="true" /></header>
    <section className="stats" aria-label="Selected subject assessment summary"><article className="stat-card mastery-stat"><strong>{selectedSubject.total.toFixed(2)}%</strong><span>{selectedSubject.code} total</span></article><article className="stat-card focus-stat"><strong className={performanceBand === 'Fail' ? 'band-fail' : 'band-pass'}>{performanceBand}</strong><span>{selectedSubject.code} performance <span className="label-nowrap">band<span className="tip"><button className="tip__trigger" type="button" aria-label="How the performance band is decided" aria-describedby="performance-band-tip"><Info size={14} aria-hidden="true" /></button><span className="tip__pop" id="performance-band-tip" role="tooltip">The subject's weighted total mapped to a grade band: below 50% Fail, 50–59% Pass, 60–69% Credit, 70–79% Distinction, 80% and above High Distinction. Formative only — not an official grade.</span></span></span></span></article><article className="stat-card assessment-stat"><strong>{selectedSubject.assessments.length}</strong><span>Assessments in {selectedSubject.code}</span></article></section>
    <section className="results-panel" aria-labelledby="assessment-results-heading"><div className="panel-heading"><h2 id="assessment-results-heading">Assessment results</h2><p>{studentId} · {selectedSubject.code}</p></div><div className="subject-results"><section className="subject-section" aria-labelledby={`${selectedSubject.code}-heading`}><header className="subject-header"><div><p className="eyebrow">Subject</p><h3 id={`${selectedSubject.code}-heading`}>{selectedSubject.code}</h3></div><p className="subject-total"><span>Subject total</span><strong>{selectedSubject.total.toFixed(2)}%</strong></p></header><div className="table-scroll"><table><thead><tr><th scope="col">Assessment</th><th scope="col">Score</th><th scope="col">Feedback comment</th><th scope="col">SILO</th><th scope="col">Weight</th><th scope="col">Weighted score</th></tr></thead><tbody>{selectedSubject.assessments.map((assessment) => <tr key={assessment.assessment}><th scope="row">{assessment.assessment}</th><td><span className="score">{assessment.score}</span></td><td className="feedback">{assessment.feedback}</td><td className="silos">{assessment.silos}</td><td>{formatPercentage(assessment.weight)}</td><td className="weighted-score">{assessment.weightedScore.toFixed(2)}</td></tr>)}</tbody></table></div></section></div></section>
    <section className="results-panel map-panel" aria-labelledby="assessment-map-heading"><div className="panel-heading"><h2 id="assessment-map-heading">Assessment map</h2><p>{selectedSubject.code} · {mapEntries.length} assessments</p></div><div className="subject-results"><section className="subject-section" aria-labelledby={`${selectedSubject.code}-map-heading`}><header className="subject-header"><div><p className="eyebrow">Subject</p><h3 id={`${selectedSubject.code}-map-heading`}>{selectedSubject.code}</h3></div></header><div className="table-scroll"><table><thead><tr><th scope="col">Assessment</th><th scope="col">Weight</th><th scope="col">Contribution</th><th scope="col">Early assessment</th><th scope="col">Hurdle</th><th scope="col">SILOs</th></tr></thead><tbody>{mapEntries.map((entry) => <tr key={entry.assessment}><th scope="row">{entry.assessment}</th><td>{formatPercentage(entry.weight)}</td><td>{entry.contribution}</td><td>{entry.earlyAssessment ? 'Yes' : 'No'}</td><td>{entry.hurdle ? 'Yes' : 'No'}</td><td className="silos">{entry.silos}</td></tr>)}</tbody></table></div></section></div></section>
    <section className="results-panel silo-panel" aria-labelledby="subject-silos-heading"><div className="panel-heading"><h2 id="subject-silos-heading">Subject learning outcomes</h2><p>{selectedSubject.code} · {silos.length} SILOs</p></div><div className="subject-results"><section className="subject-section" aria-labelledby={`${selectedSubject.code}-silos-heading`}><header className="subject-header"><div><p className="eyebrow">Subject</p><h3 id={`${selectedSubject.code}-silos-heading`}>{selectedSubject.code}</h3></div></header><div className="table-scroll"><table><thead><tr><th scope="col">SILO</th><th scope="col">Description</th></tr></thead><tbody>{silos.map((silo) => <tr key={silo.id}><th scope="row">{silo.id}</th><td>{silo.description}</td></tr>)}</tbody></table></div></section></div></section>
    <footer>Source: CSE results workbook. Scores and feedback are presented for the selected student record.</footer>
  </main>
}
