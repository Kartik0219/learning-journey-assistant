import { useMemo, useState, type FormEvent } from 'react'
import { CalendarDays, ChevronLeft, ChevronRight, Plus, X } from 'lucide-react'
import { api } from '../api'
import { MelbourneClock } from '../Clock'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { addDays, dateKey, formatKey, keys, melbourneDateKey, parseKey, readLocal, weekdayIndex, writeLocal, type KeyDate, type QuizRecord, type WeekPlan } from '../local'

/* Month calendar on Melbourne time: the week plan, quiz self-checks and the
   student's own key dates (the workbook has no due dates, so students add
   theirs). Everything shown comes from this browser's storage.

   A day can carry a plan step, several quiz results and a key date all at
   once, which is more than a small cell can print without overlapping - so
   the grid shows at most two chips per day plus a "+N more" count, and
   clicking any day opens its full, untruncated detail below the grid
   (defaulting to today). That side panel also carries the empty state, so
   an unused calendar reads as "nothing here yet" rather than a wall of
   blank boxes. */

const WEEKDAYS = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']
const MAX_CHIPS_SHOWN = 2

interface DayItems {
  due: KeyDate[]
  planned: WeekPlan['days'][string]
  quiz: QuizRecord[]
}

function DayDetail({ items, onRemoveDate }: { items: DayItems; onRemoveDate: (id: string) => void }) {
  const { due, planned, quiz } = items
  if (due.length === 0 && planned.length === 0 && quiz.length === 0) {
    return <p className="empty-note">Nothing here yet. Add a key date on the right, or drag a step onto this day from <em>Study → My week</em>.</p>
  }
  return (
    <ul className="day-detail">
      {due.map((x) => (
        <li key={x.id} className="day-detail-row due">
          <span className="cal-chip due">key date</span>
          <span><strong>{x.subject ? `${x.subject} · ` : ''}{x.title}</strong></span>
          <button type="button" className="icon-btn" aria-label={`Remove ${x.title}`} onClick={() => onRemoveDate(x.id)}><X size={13} aria-hidden="true" /></button>
        </li>
      ))}
      {planned.map((s) => (
        <li key={s.id} className="day-detail-row plan">
          <span className="cal-chip plan">planned</span>
          <span><strong>{s.code}</strong> <span className="sub">{s.subject} · {s.minutes} min</span></span>
        </li>
      ))}
      {quiz.map((q, i) => (
        <li key={i} className="day-detail-row quiz">
          <span className={`cal-chip quiz${q.gotIt / q.total >= 0.6 ? ' good' : ''}`}>quiz</span>
          <span><strong>{q.code}</strong> <span className="sub">{q.subject} · {q.gotIt} of {q.total} got it</span></span>
        </li>
      ))}
    </ul>
  )
}

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
  const [selectedDay, setSelectedDay] = useState(today)

  function itemsFor(key: string): DayItems {
    return { due: dates.filter((x) => x.date === key), planned: plan.days[key] ?? [], quiz: quizzes.filter((q) => q.date === key) }
  }

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
              const { due, planned, quiz } = itemsFor(key)
              const chips = [
                ...due.map((x) => ({ key: `due-${x.id}`, cls: 'due', text: `${x.subject ? `${x.subject} · ` : ''}${x.title}` })),
                ...planned.map((s) => ({ key: `plan-${s.id}`, cls: 'plan', text: `${s.code} · ${s.minutes}m` })),
                ...quiz.map((q, i) => ({ key: `quiz-${i}`, cls: `quiz${q.gotIt / q.total >= 0.6 ? ' good' : ''}`, text: `Quiz ${q.code} ${q.gotIt}/${q.total}` })),
              ]
              const shown = chips.slice(0, MAX_CHIPS_SHOWN)
              const hidden = chips.length - shown.length
              const cls = ['cal-cell', m !== view.m ? 'other' : '', key === today ? 'cal-today' : '', key < today ? 'past' : '', key === selectedDay ? 'cal-selected' : ''].filter(Boolean).join(' ')
              return (
                <button type="button" key={key} className={cls} onClick={() => setSelectedDay(key)} aria-pressed={key === selectedDay} aria-label={`${formatKey(key, { weekday: 'long', day: 'numeric', month: 'long' })}${chips.length ? `, ${chips.length} item${chips.length === 1 ? '' : 's'}` : ''}`}>
                  <span className="cal-num">{d}</span>
                  <div className="cal-items">
                    {shown.map((c) => <span key={c.key} className={`cal-chip ${c.cls}`}>{c.text}</span>)}
                    {hidden > 0 && <span className="cal-chip more">+{hidden} more</span>}
                  </div>
                </button>
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
          <section className="panel" aria-live="polite">
            <div className="panel-head">
              <h2><CalendarDays size={16} aria-hidden="true" className="inline-icon" /> {formatKey(selectedDay, { weekday: 'long', day: 'numeric', month: 'long' })}{selectedDay === today && <span className="chip neutral day-badge">today</span>}</h2>
            </div>
            <DayDetail items={itemsFor(selectedDay)} onRemoveDate={(id) => save(dates.filter((d) => d.id !== id))} />
          </section>
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
                      <button type="button" className="upcoming-link" onClick={() => setSelectedDay(x.date)}><strong>{x.subject ? `${x.subject} · ` : ''}{x.title}</strong><br /><span className="sub">{formatKey(x.date, { weekday: 'long', day: 'numeric', month: 'long' })}</span></button>
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
      <footer className="footer-note">Your plan, quiz history and key dates are stored only in this browser. They will not appear on another device, and clearing your browsing data clears them too.</footer>
    </main>
  )
}
