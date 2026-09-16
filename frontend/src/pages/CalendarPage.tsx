import { useMemo, useState, type FormEvent } from 'react'
import { ChevronLeft, ChevronRight, Plus, X } from 'lucide-react'
import { api } from '../api'
import { MelbourneClock } from '../Clock'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { addDays, dateKey, formatKey, keys, melbourneDateKey, parseKey, readLocal, weekdayIndex, writeLocal, type KeyDate, type QuizRecord, type WeekPlan } from '../local'

/* Month calendar on Melbourne time: the week plan, quiz self-checks and the
   student's own key dates (the workbook has no due dates, so students add
   theirs). Everything shown comes from this browser's storage. */

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

export function CalendarPage() {
  const { studentId, studentLabel } = useStudent()
  const results = useApi(() => api.results(studentId), `results-${studentId}`)
  const today = melbourneDateKey()
  const t = parseKey(today)
  const [view, setView] = useState({ y: t.y, m: t.m })
  const [dates, setDates] = useState<KeyDate[]>(() => readLocal(keys.dates(studentId), []))
  const plan = readLocal<WeekPlan>(keys.plan(studentId), { hours: 0, days: {} })
  const quizzes = readLocal<QuizRecord[]>(keys.quiz(studentId), [])
  const subjects = results.data?.subjects.map((s) => s.code) ?? []
  const [form, setForm] = useState({ date: today, title: '', subject: '' })

  const cells = useMemo(() => {
    const first = dateKey(view.y, view.m, 1)
    const start = addDays(first, -weekdayIndex(first))
    return Array.from({ length: 42 }, (_, i) => addDays(start, i))
  }, [view])

  function save(next: KeyDate[]) { setDates(next); writeLocal(keys.dates(studentId), next) }
  function add(e: FormEvent) {
    e.preventDefault()
    if (!form.title.trim() || !form.date) return
    save([...dates, { id: `${Date.now()}`, date: form.date, title: form.title.trim(), subject: form.subject }])
    setForm({ date: form.date, title: '', subject: form.subject })
  }
  const shift = (n: number) => setView((v) => { const d = new Date(Date.UTC(v.y, v.m + n, 1)); return { y: d.getUTCFullYear(), m: d.getUTCMonth() } })
  const monthLabel = new Intl.DateTimeFormat('en-AU', { timeZone: 'UTC', month: 'long', year: 'numeric' }).format(new Date(Date.UTC(view.y, view.m, 1)))
  const upcoming = [...dates].filter((d) => d.date >= today).sort((a, b) => a.date.localeCompare(b.date)).slice(0, 6)
  const daysUntil = (key: string) => Math.round((Date.UTC(parseKey(key).y, parseKey(key).m, parseKey(key).d) - Date.UTC(t.y, t.m, t.d)) / 86_400_000)

  return (
    <main className="page" id="calendar">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · calendar</p>
          <h1>{monthLabel}</h1>
          <p className="sub">Your week plan, quiz self-checks and key dates, on Melbourne time.</p>
        </div>
        <div className="cal-tools">
          <MelbourneClock large />
          <div className="week-nav">
            <button type="button" className="btn ghost" aria-label="Previous month" onClick={() => shift(-1)}><ChevronLeft size={16} aria-hidden="true" /></button>
            <button type="button" className="btn ghost" onClick={() => setView({ y: t.y, m: t.m })}>Today</button>
            <button type="button" className="btn ghost" aria-label="Next month" onClick={() => shift(1)}><ChevronRight size={16} aria-hidden="true" /></button>
          </div>
        </div>
      </header>

      <div className="cal-layout">
        <section className="panel cal-panel" aria-label={`Calendar for ${monthLabel}`}>
          <div className="cal-grid cal-head">{WEEKDAYS.map((w) => <span key={w}>{w}</span>)}</div>
          <div className="cal-grid">
            {cells.map((key) => {
              const { m, d } = parseKey(key)
              const planned = plan.days[key] ?? []
              const quiz = quizzes.filter((q) => q.date === key)
              const due = dates.filter((x) => x.date === key)
              const cls = ['cal-cell', m !== view.m ? 'other' : '', key === today ? 'cal-today' : '', key < today ? 'past' : ''].filter(Boolean).join(' ')
              return (
                <div key={key} className={cls} aria-label={formatKey(key, { weekday: 'long', day: 'numeric', month: 'long' })}>
                  <span className="cal-num">{d}</span>
                  <div className="cal-items">
                    {due.map((x) => <span key={x.id} className="cal-chip due" title={x.title}>{x.subject ? `${x.subject} · ` : ''}{x.title}</span>)}
                    {planned.map((s) => <span key={s.id} className="cal-chip plan" title={`${s.code} · ${s.minutes} min`}>{s.code} · {s.minutes}m</span>)}
                    {quiz.map((q, i) => <span key={i} className={`cal-chip quiz ${q.gotIt / q.total >= 0.6 ? 'good' : ''}`} title={`Quiz ${q.code}: ${q.gotIt} of ${q.total}`}>Quiz {q.code} {q.gotIt}/{q.total}</span>)}
                  </div>
                </div>
              )
            })}
          </div>
          <ul className="legend cal-legend" aria-label="Calendar key">
            <li><span className="cal-chip due">key date</span></li>
            <li><span className="cal-chip plan">planned study</span></li>
            <li><span className="cal-chip quiz good">quiz self-check</span></li>
          </ul>
        </section>

        <div className="stack">
          <section className="panel">
            <div className="panel-head"><h2>Add a key date</h2><p className="sub">Due dates, exams, a meeting with your tutor. Stored only in this browser.</p></div>
            <form className="date-form" onSubmit={add}>
              <label>Date<input type="date" required value={form.date} onChange={(e) => setForm({ ...form, date: e.target.value })} /></label>
              <label>Subject<select value={form.subject} onChange={(e) => setForm({ ...form, subject: e.target.value })}><option value="">—</option>{subjects.map((s) => <option key={s} value={s}>{s}</option>)}</select></label>
              <label>What<input type="text" required maxLength={60} placeholder="Assignment due" value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} /></label>
              <button type="submit" className="btn"><Plus size={15} aria-hidden="true" /> Add</button>
            </form>
          </section>
          <section className="panel">
            <div className="panel-head"><h2>Coming up</h2></div>
            {upcoming.length === 0 ? <p className="empty-note">No key dates yet. Add your assessment due dates above and the Today strip can count down to them.</p> : (
              <ul className="upcoming">
                {upcoming.map((x) => {
                  const n = daysUntil(x.date)
                  return (
                    <li key={x.id}>
                      <span className={`chip ${n <= 3 ? 'atRisk' : n <= 10 ? 'developing' : 'neutral'}`}>{n === 0 ? 'today' : n === 1 ? 'tomorrow' : `${n} days`}</span>
                      <span><strong>{x.subject ? `${x.subject} · ` : ''}{x.title}</strong><br /><span className="sub">{formatKey(x.date, { weekday: 'long', day: 'numeric', month: 'long' })}</span></span>
                      <button type="button" className="icon-btn" aria-label={`Remove ${x.title}`} onClick={() => save(dates.filter((d) => d.id !== x.id))}><X size={13} aria-hidden="true" /></button>
                    </li>
                  )
                })}
              </ul>
            )}
          </section>
        </div>
      </div>
      <footer className="footer-note">Formative only. The calendar shows what you planned and checked yourself on; it never changes a mark.</footer>
    </main>
  )
}
