import { useMemo, useState } from 'react'
import { CheckCircle2, Shuffle } from 'lucide-react'
import { api, masteryBand } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'
import { keys, melbourneDateKey, readLocal, writeLocal, type QuizRecord } from '../local'

interface Item {
  id: number
  outcomeId: number
  recId: number | null
  code: string
  subject: string
  description: string
  type: string
  prompt: string
  answerTitle: string | null
  answerText: string | null
}

// The generator embeds the grounding inside the question; show a clean prompt
// and reveal the grounded answer only after the student has tried.
function cleanPrompt(text: string): string {
  let cut = text.indexOf('Ground your answer in')
  if (cut === -1) cut = text.indexOf('No topic material')
  return (cut === -1 ? text : text.slice(0, cut)).trim()
}

function shuffle<T>(items: T[]): T[] {
  const copy = [...items]
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1))
    ;[copy[i], copy[j]] = [copy[j], copy[i]]
  }
  return copy
}

/** Self-check ring: the share of answered questions on one outcome rated "got it". */
function Ring({ pct }: { pct: number }) {
  const r = 15, c = 2 * Math.PI * r
  return (
    <svg viewBox="0 0 40 40" aria-hidden="true">
      <circle className="mini-track" cx="20" cy="20" r={r} />
      <circle className="mini-fill" cx="20" cy="20" r={r} strokeDasharray={`${(c * pct) / 100} ${c}`} transform="rotate(-90 20 20)" />
    </svg>
  )
}

export function QuizzesPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.dashboard(studentId), studentId)
  const [count, setCount] = useState('5')
  const [quiz, setQuiz] = useState<Item[]>([])
  const [checked, setChecked] = useState<Record<number, boolean>>({})
  const [ratings, setRatings] = useState<Record<number, boolean>>({})
  const [finished, setFinished] = useState(false)
  const [practised, setPractised] = useState<Record<number, 'saving' | 'done'>>({})

  const pool: Item[] = useMemo(
    () => (data?.outcomes ?? []).flatMap((o) => o.quiz_questions.map((q) => ({
      id: q.id, outcomeId: o.id, recId: o.recommendation?.id ?? null, code: o.code, subject: o.subject_code, description: o.description,
      type: q.question_type, prompt: cleanPrompt(q.question_text), answerTitle: q.answer_title, answerText: q.answer_text,
    }))),
    [data],
  )

  if (loading) return <p className="page-status">Loading your quizzes…</p>
  if (error) return <PageError error={error} />

  function generate() {
    const n = count === 'all' ? pool.length : Math.min(Number(count), pool.length)
    setQuiz(shuffle(pool).slice(0, n))
    setChecked({}); setRatings({}); setFinished(false); setPractised({})
  }

  // Per-outcome tallies from what has been rated so far.
  const tallies = quiz.reduce<Record<string, { code: string; subject: string; outcomeId: number; recId: number | null; got: number; answered: number }>>((acc, item, index) => {
    const k = `${item.subject}:${item.code}`
    acc[k] ??= { code: item.code, subject: item.subject, outcomeId: item.outcomeId, recId: item.recId, got: 0, answered: 0 }
    if (ratings[index] !== undefined) { acc[k].answered += 1; if (ratings[index]) acc[k].got += 1 }
    return acc
  }, {})
  const rated = Object.values(tallies).filter((t) => t.answered > 0)
  const gotIt = Object.values(ratings).filter(Boolean).length
  const answered = Object.keys(ratings).length

  function finish() {
    setFinished(true)
    const date = melbourneDateKey(), at = new Date().toISOString()
    const records: QuizRecord[] = rated.map((t) => ({ at, date, code: t.code, subject: t.subject, gotIt: t.got, total: t.answered }))
    writeLocal(keys.quiz(studentId), [...readLocal<QuizRecord[]>(keys.quiz(studentId), []), ...records].slice(-200))
  }
  async function practise(outcomeId: number, recId: number) {
    setPractised((p) => ({ ...p, [outcomeId]: 'saving' }))
    try { await api.markPractised(recId); setPractised((p) => ({ ...p, [outcomeId]: 'done' })) } catch { setPractised((p) => { const n = { ...p }; delete n[outcomeId]; return n }) }
  }

  return (
    <main className="page" id="quizzes">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · practice quizzes</p>
          <h1>Check yourself</h1>
        </div>
      </header>

      {pool.length === 0 ? (
        <p className="page-status">No practice questions yet — they are generated from your recorded skill gaps.</p>
      ) : (
        <>
          <section className="panel quiz-controls">
            <label htmlFor="quiz-count">Questions</label>
            <select id="quiz-count" value={count} onChange={(e) => setCount(e.target.value)}>
              <option value="3">3</option>
              <option value="5">5</option>
              <option value="10">10</option>
              <option value="all">All</option>
            </select>
            <button className="btn" type="button" onClick={generate}><Shuffle size={15} aria-hidden="true" /> {quiz.length ? 'New quiz' : 'Generate a random quiz'}</button>
            <span className="sub">{pool.length} question{pool.length === 1 ? '' : 's'} built from your own gaps</span>
          </section>

          {rated.length > 0 && (
            <section className="panel" aria-live="polite" aria-label="Self-check so far">
              <div className="quiz-rings">
                <strong>{gotIt} of {answered} so far</strong>
                {rated.map((t) => {
                  const pct = (t.got / t.answered) * 100
                  return (
                    <span key={`${t.subject}:${t.code}`} className={`ring-item ${masteryBand(pct).status}`}>
                      <Ring pct={pct} /><span><strong>{t.code}</strong> <span className="sub">{t.subject}</span><br /><span className="sub">{t.got}/{t.answered} got it</span></span>
                    </span>
                  )
                })}
              </div>
            </section>
          )}

          {quiz.map((item, index) => (
            <section className={`panel quiz-card${checked[index] ? ' checked' : ''}`} key={`${item.id}-${index}`}>
              <div className="plan-head">
                <h2><span className="step-n">{index + 1}</span> {item.code} · {item.description}</h2>
                <span className="chip neutral">{item.type}</span>
              </div>
              <p className="quiz-prompt">{item.prompt}</p>
              <label className="sr-only" htmlFor={`answer-${index}`}>Your answer to question {index + 1}</label>
              <textarea id={`answer-${index}`} rows={3} placeholder="Type your answer…" />
              {!checked[index]
                ? <div className="quiz-actions"><button className="btn ghost" type="button" onClick={() => setChecked((c) => ({ ...c, [index]: true }))}>Check my answer</button></div>
                : (
                  <div className={`answer${ratings[index] === true ? ' correct' : ratings[index] === false ? ' review' : ''}`}>
                    {item.answerText
                      ? <><p className="material-title">{item.answerTitle ?? 'Model answer'}</p><p>{item.answerText}</p></>
                      : <p>No model material is recorded for this outcome yet — compare your answer with your marker's feedback on the Results page.</p>}
                    <div className="rating" role="radiogroup" aria-label={`How did you go on question ${index + 1}?`}>
                      <span className="sub">How did you go?</span>
                      <label><input type="radio" name={`rate-${index}`} checked={ratings[index] === true} onChange={() => setRatings((r) => ({ ...r, [index]: true }))} /> Got it</label>
                      <label><input type="radio" name={`rate-${index}`} checked={ratings[index] === false} onChange={() => setRatings((r) => ({ ...r, [index]: false }))} /> Need review</label>
                    </div>
                  </div>
                )}
            </section>
          ))}

          {quiz.length > 0 && (
            <section className="panel quiz-controls">
              {!finished
                ? <button className="btn" type="button" disabled={answered === 0} onClick={finish}>Finish quiz{answered < quiz.length ? ` (${answered} of ${quiz.length} rated)` : ''}</button>
                : (
                  <div className="stack">
                    <span><strong>You got {gotIt} of {answered}</strong> — {rated.map((t) => `${t.code} ${t.got}/${t.answered}`).join(' · ')}. Saved to your calendar.</span>
                    <div className="quiz-actions">
                      {rated.filter((t) => t.recId !== null).map((t) => (
                        <button key={t.outcomeId} className={practised[t.outcomeId] === 'done' ? 'btn ghost done' : 'btn ghost'} type="button" disabled={Boolean(practised[t.outcomeId])} onClick={() => practise(t.outcomeId, t.recId!)}>
                          <CheckCircle2 size={14} aria-hidden="true" /> {practised[t.outcomeId] === 'done' ? <>{t.code} boost applied</> : practised[t.outcomeId] === 'saving' ? 'Saving…' : `Mark ${t.code} as practised`}
                        </button>
                      ))}
                    </div>
                  </div>
                )}
              <span className="sub">A private self-check — nothing is marked against you. Marking an outcome as practised gives it a small, capped boost.</span>
            </section>
          )}
        </>
      )}
    </main>
  )
}
