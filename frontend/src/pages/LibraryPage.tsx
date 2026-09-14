import { useMemo, useState } from 'react'
import { BookOpen, ExternalLink } from 'lucide-react'
import { api, type LibraryMaterial } from '../api'
import { Dropdown } from '../Dropdown'
import { useApi } from '../useApi'
import { PageError } from './PageError'

function MaterialCard({ m }: { m: LibraryMaterial }) {
  return (
    <article className="material resource">
      <div className="material-head">
        <p className="material-title">{m.title}</p>
        {m.provenance === 'curated' && <span className="chip muted">curated</span>}
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

export function LibraryPage() {
  const { data, error, loading } = useApi(() => api.library(), 'library')

  const allSubjectCodes = useMemo(() => (data?.subjects.map((s) => s.code) ?? []).sort(), [data])
  const [subjectCode, setSubjectCode] = useState('')
  const activeCode = allSubjectCodes.includes(subjectCode) ? subjectCode : allSubjectCodes[0]

  if (loading) return <p className="page-status">Loading the resource library…</p>
  if (error) return <PageError error={error} />

  const subject = data?.subjects.find((s) => s.code === activeCode)
  const totalMaterials = subject?.silos.reduce((n, s) => n + s.materials.length, 0) ?? 0

  return (
    <main className="page" id="library">
      <header className="page-head">
        <div>
          <p className="eyebrow">resource library</p>
          <h1>Every resource, by SILO</h1>
          {subject && <p className="sub">{totalMaterials} resources across {subject.silos.length} SILO{subject.silos.length === 1 ? '' : 's'} in {subject.code}.</p>}
        </div>
        {allSubjectCodes.length > 1 && <Dropdown label="Subject" ariaLabel="Choose subject" icon={BookOpen} value={activeCode} options={allSubjectCodes.map((code) => ({ value: code, label: code }))} onChange={setSubjectCode} />}
      </header>

      {!subject || subject.silos.length === 0 ? (
        <section className="panel">
          <p className="empty-note">No study material has been loaded yet.</p>
        </section>
      ) : subject.silos.map((silo) => (
        <section className="panel" key={silo.code}>
          <div className="panel-head">
            <h2>{silo.code}</h2>
            <p className="sub">{silo.materials.length} resource{silo.materials.length === 1 ? '' : 's'}</p>
          </div>
          {silo.description && <p className="material-title">{silo.description}</p>}
          <div className="materials">
            {silo.materials.map((m) => <MaterialCard m={m} key={m.title} />)}
          </div>
        </section>
      ))}
      <footer className="footer-note">The full study-material catalogue for every subject and SILO, not filtered to your own mastery. See Resources for your personalised, weakest-first list.</footer>
    </main>
  )
}
