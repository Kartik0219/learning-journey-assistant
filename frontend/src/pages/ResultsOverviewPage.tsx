import { useState } from 'react'
import { api, assessmentName, performanceBand, subjectTotal, type SubjectResults } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

const SEGMENT_TONES = ['#B8B3B3', '#7A7575', '#4A4646', '#E2001A', '#9E1B32', '#1A1A1A']

function SubjectCard({ subject, selected, onSelect }: { subject: SubjectResults; selected: boolean; onSelect: () => void }) {
  const total = subjectTotal(subject)
  const band = total === null ? null : performanceBand(total)
  return (
    <button type="button" className={selected ? 'subject-card selected' : 'subject-card'} aria-pressed={selected} onClick={onSelect}>
      <span className="stat-label">{subject.code}</span>
      <span className="stat-value">{total === null ? '—' : total.toFixed(2)}</span>
      {band && <span className={`chip ${band.status}`}>{band.label}</span>}
    </button>
  )
}

export function ResultsOverviewPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.results(studentId), studentId)
  const [subjectCode, setSubjectCode] = useState('')

  if (loading) return <p className="page-status">Loading results…</p>
  if (error) return <PageError error={error} />
  if (!data || data.subjects.length === 0) return <p className="page-status">No assessment results recorded for {studentLabel}.</p>

  const subject = data.subjects.find((s) => s.code === subjectCode) ?? data.subjects[0]
  const total = subjectTotal(subject)
  const band = total === null ? null : performanceBand(total)
  const weighted = subject.assessments.every((r) => r.weighted_score !== null)
  const descriptions = Object.fromEntries(subject.learning_outcomes.map((lo) => [lo.code, lo.description]))

  return (
    <main className="page" id="results-overview">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · results</p>
          <h1>Every assessment, as recorded</h1>
        </div>
      </header>

      <section className="subject-cards" aria-label="Subject totals">
        {data.subjects.map((s) => <SubjectCard key={s.code} subject={s} selected={s.code === subject.code} onSelect={() => setSubjectCode(s.code)} />)}
      </section>

      <section className="panel">
        <div className="subject-head">
          <div>
            <h2>{subject.code}</h2>
            {subject.name && subject.name !== subject.code && <p className="sub">{subject.name}</p>}
          </div>
          {total !== null && (
            <div className="total">{weighted ? 'Weighted total' : 'Average score'} <strong>{total.toFixed(2)}</strong>{band && <span className={`chip ${band.status}`}>{band.label}</span>}</div>
          )}
        </div>

        {weighted && (
          <div className="wbar" role="img" aria-label={`How the total is built: ${subject.assessments.map((r) => `${assessmentName(r.assessment)} ${r.weighted_score?.toFixed(2)}`).join(', ')}`}>
            {subject.assessments.map((r, i) => (
              <span key={r.id} style={{ width: `${r.weighted_score}%`, background: SEGMENT_TONES[i % SEGMENT_TONES.length] }} title={`${assessmentName(r.assessment)}: ${r.weighted_score?.toFixed(2)}`} />
            ))}
          </div>
        )}

        <div className="table-scroll">
          <table className="results-table">
            <thead>
              <tr><th scope="col">Assessment Type</th><th scope="col">Score (1-100)</th><th scope="col">Feedback Comment</th><th scope="col">SILO's</th><th scope="col">Weight</th><th scope="col">Weighted Score</th></tr>
            </thead>
            <tbody>
              {subject.assessments.map((row) => (
                <tr key={row.id}>
                  <th scope="row">{assessmentName(row.assessment)}</th>
                  <td className="num">{row.score ?? '—'}</td>
                  <td className="fb">{row.feedback ?? '—'}</td>
                  <td>
                    <div className="silo-list">
                      {row.silo_codes.length ? row.silo_codes.map((code) => (
                        <span key={code} className="silo-item"><strong>{code}</strong>{descriptions[code] ? `: ${descriptions[code]}` : ''}</span>
                      )) : '—'}
                    </div>
                  </td>
                  <td className="num">{row.weight === null ? '—' : `${Math.round(row.weight * 100)}%`}</td>
                  <td className="num">{row.weighted_score === null ? '—' : row.weighted_score.toFixed(2)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>
      <footer className="footer-note">Source: your marked results as imported — read-only, nothing is written back to Moodle. Bands are formative, not official grades.</footer>
    </main>
  )
}
