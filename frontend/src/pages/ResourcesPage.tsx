import { useMemo, useState } from 'react'
import { BookOpen, ExternalLink } from 'lucide-react'
import { api, masteryBand, type Material } from '../api'
import { Dropdown } from '../Dropdown'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

function MaterialCard({ m }: { m: Material }) {
  const focus = m.mastery_pct !== null && m.mastery_pct < 65
  return (
    <article className={`material resource${focus ? ' focus' : ''}`}>
      <div className="material-head">
        <p className="material-title">{m.title}</p>
      </div>
      <p>{m.passage_text}</p>
      {m.source_url && (
        <a className="material-link" href={m.source_url} target="_blank" rel="noopener noreferrer">
          Open resource <ExternalLink size={13} aria-hidden="true" />
        </a>
      )}
    </article>
  )
}

export function ResourcesPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.resources(studentId), studentId)

  const allSubjectCodes = useMemo(() => (data?.subjects.map((s) => s.code) ?? []).sort(), [data])
  const [subjectCode, setSubjectCode] = useState('')
  const activeCode = allSubjectCodes.includes(subjectCode) ? subjectCode : allSubjectCodes[0]

  if (loading) return <p className="page-status">Loading resources…</p>
  if (error) return <PageError error={error} />

  const subjects = (data?.subjects ?? [])
    .filter((s) => !activeCode || s.code === activeCode)
    .sort((a, b) => a.code.localeCompare(b.code))
  const total = subjects.reduce((n, s) => n + s.silos.reduce((m, silo) => m + silo.materials.length, 0), 0)
  const anyCurated = subjects.some((s) => s.silos.some((silo) => silo.materials.some((m) => m.provenance === 'curated')))

  return (
    <main className="page" id="resources">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · resources</p>
          <h1>What to read for each outcome</h1>
          {total > 0 && <p className="sub">{total} resources across {subjects.length} subject{subjects.length === 1 ? '' : 's'}.</p>}
        </div>
        {allSubjectCodes.length > 1 && <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={allSubjectCodes.map((code) => ({ value: code, label: code }))} onChange={setSubjectCode} />}
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
            <p className="sub">{subject.silos.reduce((n, silo) => n + silo.materials.length, 0)} resource{subject.silos.reduce((n, silo) => n + silo.materials.length, 0) === 1 ? '' : 's'}</p>
          </div>
          {subject.silos.map((silo) => (
            <div className="materials-group" key={silo.code}>
              <h3 className="silo-heading">
                {silo.code}
                {silo.mastery_pct !== null && <span className={`chip ${masteryBand(silo.mastery_pct).status}`}>{silo.mastery_pct}% · {masteryBand(silo.mastery_pct).label}</span>}
              </h3>
              {silo.description && <p className="sub silo-description">{silo.description}</p>}
              <div className="materials">
                {silo.materials.map((m) => <MaterialCard m={m} key={m.title} />)}
              </div>
            </div>
          ))}
        </section>
      ))}
      <footer className="footer-note">Links open in a new tab on the publisher's own site. The Learning Journey Assistant never generates study material — every item here is a real resource a person chose.</footer>
    </main>
  )
}
