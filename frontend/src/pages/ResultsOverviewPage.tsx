import { useState } from 'react'
import { BookOpen } from 'lucide-react'
import { api, masteryBand } from '../api'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

export function ResultsOverviewPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.results(studentId), studentId)
  const [subjectCode, setSubjectCode] = useState('')

  if (loading) return <p className="page-status">Loading results…</p>
  if (error) return <PageError error={error} />
  if (!data || data.subjects.length === 0) return <p className="page-status">No assessment results recorded for {studentLabel}.</p>

  const subject = data.subjects.find((s) => s.code === subjectCode) ?? data.subjects[0]
  const average = subject.average_score

  return <main className="dashboard" id="results-overview">
    <header className="dashboard-header results-header"><div><p className="eyebrow">{studentLabel} · assessment record</p><h1>Results overview <span className="title-subject">{subject.code}</span></h1></div><div className="header-actions">{data.subjects.length > 1 && <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={subject.code} options={data.subjects.map((s) => ({ value: s.code, label: s.code }))} onChange={setSubjectCode} />}</div><div className="header-spacer" aria-hidden="true" /></header>
    <section className="stats" aria-label="Selected subject assessment summary">
      <article className="stat-card mastery-stat"><strong>{average === null ? '—' : `${average}%`}</strong><span>Average score · {subject.code}</span></article>
      <article className="stat-card focus-stat"><strong className={average !== null && average < 50 ? 'band-fail' : 'band-pass'}>{average === null ? '—' : masteryBand(average).label}</strong><span>Band (formative)</span></article>
      <article className="stat-card assessment-stat"><strong>{subject.assessments.length}</strong><span>Assessments in {subject.code}</span></article>
    </section>
    <section className="results-panel" aria-labelledby="assessment-results-heading"><div className="panel-heading"><h2 id="assessment-results-heading">Assessment results</h2><p>{subject.name}</p></div><div className="subject-results"><section className="subject-section"><div className="table-scroll"><table><thead><tr><th scope="col">Assessment</th><th scope="col">Score</th><th scope="col">Feedback comment</th><th scope="col">SILOs evidenced</th></tr></thead><tbody>{subject.assessments.map((row) => <tr key={row.id}><th scope="row">{row.assessment}</th><td><span className="score">{row.score ?? '—'}</span></td><td className="feedback">{row.feedback ?? '—'}</td><td className="silos">{row.silo_codes.length ? row.silo_codes.join(', ') : '—'}</td></tr>)}</tbody></table></div></section></div></section>
    <section className="results-panel silo-panel" aria-labelledby="subject-silos-heading"><div className="panel-heading"><h2 id="subject-silos-heading">Subject learning outcomes</h2><p>{subject.code} · {subject.learning_outcomes.length} SILOs</p></div><div className="subject-results"><section className="subject-section"><div className="table-scroll"><table><thead><tr><th scope="col">SILO</th><th scope="col">Description</th></tr></thead><tbody>{subject.learning_outcomes.map((lo) => <tr key={lo.code}><th scope="row">{lo.code}</th><td>{lo.description}</td></tr>)}</tbody></table></div></section></div></section>
    <footer>Source: your marked results as imported (read-only — nothing here is written back to Moodle).</footer>
  </main>
}
