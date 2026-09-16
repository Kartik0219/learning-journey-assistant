import { useEffect, useMemo, useState, type DragEvent } from 'react'
import { CalendarDays, GripVertical, X } from 'lucide-react'
import { api, humanise, masteryBand, masteryPct, type Outcome } from '../api'
import { useStudent } from '../studentContext'
import { useApi } from '../useApi'
import { PageError } from './PageError'
import { addDays, formatKey, keys, melbourneDateKey, minutesFor, readLocal, weekOf, writeLocal, type PlannedStep, type WeekPlan } from '../local'

/* Plan my week: a budget of hours, the recommended steps weakest-first, and
   seven day columns to drop them into. Drag on a mouse; on a phone use the
   "Add to" menu. The plan lives in this browser only (local.ts). */

const EMPTY: WeekPlan = { hours: 6, days: {} }

function stepFor(o: Outcome): PlannedStep {
  return { id: o.id, code: o.code, subject: o.subject_code, method: o.recommendation?.method ?? 'practice', minutes: minutesFor(o.recommendation?.method ?? '') }
}

export function PlannerPage() {
  const { studentId, studentLabel } = useStudent()
  const { data, error, loading } = useApi(() => api.dashboard(studentId), studentId)
  const today = melbourneDateKey()
  const [weekStart, setWeekStart] = useState(() => weekOf(today)[0])
  const week = useMemo(() => weekOf(weekStart), [weekStart])
  const [plan, setPlan] = useState<WeekPlan>(() => readLocal(keys.plan(studentId), EMPTY))
  const [dragging, setDragging] = useState<number | null>(null)
  const [over, setOver] = useState<string | null>(null)

  useEffect(() => { writeLocal(keys.plan(studentId), plan) }, [plan, studentId])

  if (loading && !data) return <p className="page-status">Loading your plan…</p>
  if (error) return <PageError error={error} />

  const candidates = (data?.outcomes ?? [])
    .filter((o) => o.recommendation && o.mastery_score !== null)
    .sort((a, b) => (a.mastery_score ?? 0) - (b.mastery_score ?? 0))
  const plannedIds = new Set(week.flatMap((d) => (plan.days[d] ?? []).map((s) => s.id)))
  const unplanned = candidates.filter((o) => !plannedIds.has(o.id))
  const minutesPlanned = week.reduce((t, d) => t + (plan.days[d] ?? []).reduce((m, s) => m + s.minutes, 0), 0)
  const budget = plan.hours * 60
  const attention = candidates.filter((o) => plannedIds.has(o.id))

  function place(step: PlannedStep, day: string) {
    setPlan((p) => {
      const days = { ...p.days }
      for (const d of Object.keys(days)) days[d] = days[d].filter((s) => s.id !== step.id)
      days[day] = [...(days[day] ?? []), step]
      return { ...p, days }
    })
  }
  function remove(id: number) {
    setPlan((p) => {
      const days = { ...p.days }
      for (const d of Object.keys(days)) days[d] = days[d].filter((s) => s.id !== id)
      return { ...p, days }
    })
  }
  function onDrop(e: DragEvent, day: string) {
    e.preventDefault()
    const id = Number(e.dataTransfer.getData('text/plain') || dragging)
    const o = candidates.find((c) => c.id === id)
    if (o) place(stepFor(o), day)
    setDragging(null); setOver(null)
  }

  return (
    <main className="page" id="planner">
      <header className="page-head">
        <div>
          <p className="eyebrow">{studentLabel} · plan my week</p>
          <h1>Where does the time go?</h1>
          <p className="sub">Set the hours you have, then drag steps onto days. Weakest outcomes are listed first. Your plan stays in this browser and shows on the Calendar.</p>
        </div>
        <div className="week-nav">
          <button type="button" className="btn ghost" onClick={() => setWeekStart(addDays(weekStart, -7))}>‹ Prev</button>
          <span className="week-label"><CalendarDays size={15} aria-hidden="true" /> {formatKey(week[0], { day: 'numeric', month: 'short' })} – {formatKey(week[6], { day: 'numeric', month: 'short' })}</span>
          <button type="button" className="btn ghost" onClick={() => setWeekStart(addDays(weekStart, 7))}>Next ›</button>
        </div>
      </header>

      <section className="panel budget">
        <label htmlFor="hours"><strong>Hours I can study this week</strong> <output>{plan.hours} h</output></label>
        <input id="hours" type="range" min={1} max={25} step={1} value={plan.hours} onChange={(e) => setPlan((p) => ({ ...p, hours: Number(e.target.value) }))} />
        <div className="budget-bar" role="progressbar" aria-valuemin={0} aria-valuemax={budget} aria-valuenow={minutesPlanned} aria-label="Planned study time against your budget">
          <span className={minutesPlanned > budget ? 'budget-fill over' : 'budget-fill'} style={{ width: `${Math.min(100, (minutesPlanned / Math.max(budget, 1)) * 100)}%` }} />
        </div>
        <p className="sub" aria-live="polite">
          {Math.round(minutesPlanned / 60 * 10) / 10} h planned of {plan.hours} h.
          {minutesPlanned > budget && <strong className="delta down"> Over by {Math.round((minutesPlanned - budget) / 60 * 10) / 10} h — drop something or add hours.</strong>}
          {attention.length > 0 && <> This plan gives attention to <strong>{attention.map((o) => o.code).join(', ')}</strong>{attention.length === 1 ? '' : ` (${attention.length} outcomes)`}.</>}
        </p>
        {minutesPlanned === 0 && candidates.length > 0 && (
          <p className="empty-note">Nothing planned this week yet. Drag a step from the list below onto a day — or, on a phone, use its <em>Add to…</em> menu.</p>
        )}
      </section>

      <div className="planner-grid">
        <section className="panel steps-pool" aria-label="Steps to plan">
          <div className="panel-head"><h2>Steps to place</h2><p className="sub">{unplanned.length} left · weakest first</p></div>
          {unplanned.length === 0 && <p className="empty-note">Everything is on the calendar. Drag a step back here to unplan it, or remove it with ×.</p>}
          <ul className="pool">
            {unplanned.map((o) => {
              const pct = masteryPct(o) ?? 0
              const s = stepFor(o)
              return (
                <li key={o.id} className="drag-item" draggable onDragStart={(e) => { e.dataTransfer.setData('text/plain', String(o.id)); setDragging(o.id) }} onDragEnd={() => { setDragging(null); setOver(null) }}>
                  <GripVertical size={14} aria-hidden="true" className="grip" />
                  <span className="drag-main"><strong>{o.code}</strong> <span className="silo-tag">{o.subject_code}</span> <span className={`chip ${masteryBand(pct).status}`}>{pct.toFixed(0)}%</span><br /><span className="sub">{humanise(s.method)} · about {s.minutes} min</span></span>
                  <label className="sr-only" htmlFor={`add-${o.id}`}>Add {o.code} to a day</label>
                  <select id={`add-${o.id}`} className="add-to" value="" onChange={(e) => { if (e.target.value) place(s, e.target.value) }}>
                    <option value="">Add to…</option>
                    {week.map((d) => <option key={d} value={d}>{formatKey(d, { weekday: 'short' })}</option>)}
                  </select>
                </li>
              )
            })}
          </ul>
        </section>

        <section className="week" aria-label="This week">
          {week.map((d) => {
            const items = plan.days[d] ?? []
            const mins = items.reduce((t, s) => t + s.minutes, 0)
            return (
              <div key={d} className={`day-col${over === d ? ' over' : ''}${d === today ? ' today' : ''}`} onDragOver={(e) => { e.preventDefault(); setOver(d) }} onDragLeave={() => setOver(null)} onDrop={(e) => onDrop(e, d)}>
                <div className="day-head"><strong>{formatKey(d, { weekday: 'short' })}</strong><span className="sub">{formatKey(d, { day: 'numeric', month: 'short' })}{d === today && ' · today'}</span></div>
                <ul className="day-list">
                  {items.map((s) => (
                    <li key={s.id} className="day-item" draggable onDragStart={(e) => { e.dataTransfer.setData('text/plain', String(s.id)); setDragging(s.id) }}>
                      <span><strong>{s.code}</strong> <span className="sub">{s.minutes} min</span></span>
                      <button type="button" className="icon-btn" aria-label={`Remove ${s.code} from ${formatKey(d)}`} onClick={() => remove(s.id)}><X size={13} aria-hidden="true" /></button>
                    </li>
                  ))}
                </ul>
                <div className="day-foot sub">{mins ? `${mins} min` : 'drop here'}</div>
              </div>
            )
          })}
        </section>
      </div>
      <footer className="footer-note">Minutes are rough guides per study method. Marking a step as practised on the Plan page is what nudges mastery; planning it here just keeps you honest.</footer>
    </main>
  )
}
