/* Per-student, browser-only state for the interactive features: quiz
   self-checks, the week plan, the student's own key dates and the "since
   your last visit" comparison. Nothing here is sent to the server - it is
   the student's private scratch space, and it survives only in this
   browser. Every read and write is guarded because private windows and
   locked-down browsers can throw on localStorage. */

export const MELBOURNE = 'Australia/Melbourne'

export function readLocal<T>(key: string, fallback: T): T {
  try {
    const raw = localStorage.getItem(key)
    return raw ? (JSON.parse(raw) as T) : fallback
  } catch {
    return fallback
  }
}

export function writeLocal(key: string, value: unknown): void {
  try {
    localStorage.setItem(key, JSON.stringify(value))
  } catch {
    /* storage unavailable - the feature simply does not persist */
  }
}

/** "YYYY-MM-DD" for a moment as seen on a Melbourne calendar. */
export function melbourneDateKey(at: Date = new Date()): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: MELBOURNE, year: 'numeric', month: '2-digit', day: '2-digit' }).format(at)
}

/** Hour of the day in Melbourne (0-23), for the greeting. */
export function melbourneHour(at: Date = new Date()): number {
  return Number(new Intl.DateTimeFormat('en-AU', { timeZone: MELBOURNE, hour: 'numeric', hour12: false }).format(at))
}

export function dateKey(y: number, m: number, d: number): string {
  return `${y}-${String(m + 1).padStart(2, '0')}-${String(d).padStart(2, '0')}`
}

export function parseKey(key: string): { y: number; m: number; d: number } {
  const [y, m, d] = key.split('-').map(Number)
  return { y, m: m - 1, d }
}

export function addDays(key: string, n: number): string {
  const { y, m, d } = parseKey(key)
  const dt = new Date(Date.UTC(y, m, d + n))
  return dateKey(dt.getUTCFullYear(), dt.getUTCMonth(), dt.getUTCDate())
}

/** Monday-first weekday index (0 = Monday) of a date key. */
export function weekdayIndex(key: string): number {
  const { y, m, d } = parseKey(key)
  return (new Date(Date.UTC(y, m, d)).getUTCDay() + 6) % 7
}

/** The seven date keys of the Melbourne week containing `key`, Monday first. */
export function weekOf(key: string): string[] {
  const monday = addDays(key, -weekdayIndex(key))
  return Array.from({ length: 7 }, (_, i) => addDays(monday, i))
}

export function formatKey(key: string, opts: Intl.DateTimeFormatOptions = { weekday: 'short', day: 'numeric', month: 'short' }): string {
  const { y, m, d } = parseKey(key)
  return new Intl.DateTimeFormat('en-AU', { timeZone: 'UTC', ...opts }).format(new Date(Date.UTC(y, m, d)))
}

/* ---- records ---------------------------------------------------------- */

export interface QuizRecord { at: string; date: string; code: string; subject: string; gotIt: number; total: number }
export interface PlannedStep { id: number; code: string; subject: string; method: string; minutes: number }
export interface WeekPlan { hours: number; days: Record<string, PlannedStep[]> }
export interface KeyDate { id: string; date: string; title: string; subject: string }
export interface LastVisit { at: string; totals: Record<string, number> }

export const keys = {
  quiz: (studentId: number) => `lja-quiz-${studentId}`,
  plan: (studentId: number) => `lja-plan-${studentId}`,
  dates: (studentId: number) => `lja-dates-${studentId}`,
  last: (studentId: number) => `lja-last-${studentId}`,
}

/** Rough minutes per study method, for the week plan's hours budget. */
export function minutesFor(method: string): number {
  const table: Record<string, number> = {
    worked_example: 45, spaced_practice: 30, retrieval_practice: 25, self_explanation: 35,
    practice_testing: 30, elaboration: 35, interleaving: 40, concept_mapping: 40,
  }
  return table[method] ?? 40
}
