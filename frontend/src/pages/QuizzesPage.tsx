import { useMemo, useState } from 'react'
import { Shuffle } from 'lucide-react'
import { api } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'

interface Item {
  id: number
  code: string
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

export function QuizzesPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.dashboard(studentId), studentId)
  const [count, setCount] = useState('5')
  const [quiz, setQuiz] = useState<Item[]>([])
  const [revealed, setRevealed] = useState(false)
  const [ratings, setRatings] = useState<Record<number, boolean>>({})

  const pool: Item[] = useMemo(
    () => (data?.outcomes ?? []).flatMap((o) => o.quiz_questions.map((q) => ({
      id: q.id, code: o.code, description: o.description, type: q.question_type,
      prompt: cleanPrompt(q.question_text), answerTitle: q.answer_title, answerText: q.answer_text,
    }))),
    [data],
  )

  if (loading) return <p className="page-status">Loading your quizzes…</p>
  if (error) return <PageError error={error} />

  function generate() {
    const n = count === 'all' ? pool.length : Math.min(Number(count), pool.length)
    setQuiz(shuffle(pool).slice(0, n))
    setRevealed(false)
    setRatings({})
  }

  const gotIt = Object.values(ratings).filter(Boolean).length

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

          {quiz.map((item, index) => (
            <section className="panel quiz-card" key={`${item.id}-${index}`}>
              <div className="plan-head">
                <h2><span className="step-n">{index + 1}</span> {item.code} · {item.description}</h2>
                <span className="chip neutral">{item.type}</span>
              </div>
              <p className="quiz-prompt">{item.prompt}</p>
              <label className="sr-only" htmlFor={`answer-${index}`}>Your answer to question {index + 1}</label>
              <textarea id={`answer-${index}`} rows={3} placeholder="Type your answer…" />
              {revealed && (
                <div className="answer">
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
              {!revealed
                ? <button className="btn" type="button" onClick={() => setRevealed(true)}>Finish &amp; reveal answers</button>
                : <span><strong>You rated {gotIt} / {quiz.length}</strong> as “got it”.</span>}
              <span className="sub">A private self-check — nothing is marked or recorded against you.</span>
            </section>
          )}
        </>
      )}
    </main>
  )
}
