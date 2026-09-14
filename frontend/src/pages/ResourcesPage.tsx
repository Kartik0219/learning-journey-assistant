import { api } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

export function ResourcesPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.resources(studentId), studentId)

  if (loading) return <p className="page-status">Loading resources…</p>
  if (error) return <PageError error={error} />

  const subjects = data?.subjects ?? []

  return (
    <main className="page" id="resources">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · resources</p>
          <h1>Subject materials</h1>
        </div>
      </header>
      {subjects.length === 0 ? (
        <section className="panel">
          <p className="empty-note">No subject materials have been loaded for your subjects yet. Study plans and quizzes only ever use real subject passages, so nothing is shown in their place — your coordinator has been flagged.</p>
        </section>
      ) : subjects.map((subject) => (
        <section className="panel" key={subject.code}>
          <div className="panel-head"><h2>{subject.code}</h2><p className="sub">{subject.materials.length} passage{subject.materials.length === 1 ? '' : 's'}</p></div>
          <div className="materials">
            {subject.materials.map((m) => (
              <article className="material" key={m.title}>
                <p className="material-title">{m.title} {m.learning_outcome_code && <span className="silo-tag">{m.learning_outcome_code}</span>}</p>
                <p>{m.passage_text}</p>
              </article>
            ))}
          </div>
        </section>
      ))}
    </main>
  )
}
