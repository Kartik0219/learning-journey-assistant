import { ExternalLink, PlayCircle } from 'lucide-react'
import { api, masteryBand, type Material } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

function MaterialCard({ m }: { m: Material }) {
  const band = m.mastery_pct !== null ? masteryBand(m.mastery_pct) : null
  const focus = m.mastery_pct !== null && m.mastery_pct < 65
  const isVideo = m.resource_type === 'video'
  return (
    <article className={`material resource${focus ? ' focus' : ''}`}>
      <div className="material-head">
        <p className="material-title">
          {isVideo && <PlayCircle size={14} aria-hidden="true" className="video-icon" />}
          {m.title}
          {m.learning_outcome_code && <span className="silo-tag">{m.learning_outcome_code}</span>}
          {isVideo && <span className="chip muted">video</span>}
        </p>
        {band && <span className={`chip ${band.status}`}>{m.mastery_pct}% · {band.label}</span>}
      </div>
      <p>{m.passage_text}</p>
      {m.source_url && (
        <a className="material-link" href={m.source_url} target="_blank" rel="noopener noreferrer">
          {isVideo ? 'Watch on YouTube' : 'Open resource'} <ExternalLink size={13} aria-hidden="true" />
        </a>
      )}
    </article>
  )
}

export function ResourcesPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.resources(studentId), studentId)

  if (loading) return <p className="page-status">Loading resources…</p>
  if (error) return <PageError error={error} />

  const subjects = data?.subjects ?? []
  const total = subjects.reduce((n, s) => n + s.materials.length, 0)
  const anyCurated = subjects.some((s) => s.materials.some((m) => m.provenance === 'curated'))
  const focusCount = subjects.reduce((n, s) => n + s.materials.filter((m) => m.mastery_pct !== null && m.mastery_pct < 65).length, 0)

  return (
    <main className="page" id="resources">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · resources</p>
          <h1>What to read for each outcome</h1>
          {total > 0 && <p className="sub">{total} resources across {subjects.length} subject{subjects.length === 1 ? '' : 's'}, ordered by where you need them most{focusCount ? ` — ${focusCount} sit under outcomes below 65%` : ''}.</p>}
        </div>
      </header>

      {anyCurated && (
        <p className="curated-note">
          <strong>Curated, not official.</strong> These are free, well-known resources the project team hand-picked for each learning outcome (official documentation, MIT OpenCourseWare, OWASP and similar). They are not La Trobe subject materials — your subject's own readings on the LMS take priority. Your coordinator can replace this list with official material at any time.
        </p>
      )}

      {subjects.length === 0 ? (
        <section className="panel">
          <p className="empty-note">No resources have been loaded for your subjects yet. Nothing is shown in their place — your coordinator has been flagged.</p>
        </section>
      ) : subjects.map((subject) => (
        <section className="panel" key={subject.code}>
          <div className="panel-head">
            <h2>{subject.code}</h2>
            <p className="sub">{subject.materials.length} resource{subject.materials.length === 1 ? '' : 's'} · weakest outcome first</p>
          </div>
          <div className="materials">
            {subject.materials.map((m) => <MaterialCard m={m} key={m.title} />)}
          </div>
        </section>
      ))}
      <footer className="footer-note">Links open in a new tab on the publisher's own site. The Learning Journey Assistant never generates study material — every item here is a real resource a person chose.</footer>
    </main>
  )
}
